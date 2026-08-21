import argparse
import json
import os
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from interview_intelligence.review.engines.openai_engine import OpenAIReviewEngine
from interview_intelligence.review.models import InterviewReview, ReviewRequest
from interview_intelligence.review.service import InterviewReviewService

DEFAULT_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")
DEFAULT_DB_PATH = Path.home() / "Library/Application Support/InterviewIntelligence/app.db"


class BenchmarkRow(TypedDict):
    model: str
    elapsed_seconds: float | None
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    hiring_signal: str
    confidence: float
    question_count: int
    average_question_rating: float | None


@dataclass(frozen=True)
class BenchmarkInterview:
    id: str
    company: str
    role: str | None
    target_level: str | None
    round_type: str | None
    artifact_root_path: Path


def _load_interview(database_path: Path, interview_id: str) -> BenchmarkInterview:
    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, company, role, target_level, round_type, artifact_root_path
            FROM interviews
            WHERE id = ?
            """,
            (interview_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Interview not found: {interview_id}")
    if not row["artifact_root_path"]:
        raise ValueError("Interview has not been processed yet")

    return BenchmarkInterview(
        id=str(row["id"]),
        company=str(row["company"]),
        role=row["role"],
        target_level=row["target_level"],
        round_type=row["round_type"],
        artifact_root_path=Path(str(row["artifact_root_path"])),
    )


def _safe_model_name(model: str) -> str:
    return model.replace("/", "-").replace(":", "-")


def _comparison_row(review: InterviewReview) -> BenchmarkRow:
    usage = review.usage
    analysis = review.analysis
    ratings = [q.rating for q in review.questions if q.rating is not None]
    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    return {
        "model": review.model,
        "elapsed_seconds": analysis.elapsed_seconds if analysis else None,
        "input_tokens": usage.input_tokens if usage else 0,
        "cached_input_tokens": usage.cached_input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "reasoning_tokens": usage.reasoning_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "estimated_cost_usd": usage.estimated_cost_usd if usage else None,
        "hiring_signal": review.hiring_signal.value,
        "confidence": review.confidence,
        "question_count": len(review.questions),
        "average_question_rating": average_rating,
    }


def run_benchmark(
    *,
    interview_id: str,
    models: Sequence[str],
    database_path: Path = DEFAULT_DB_PATH,
    output_root: Path | None = None,
) -> tuple[Path, list[BenchmarkRow]]:
    interview = _load_interview(database_path.expanduser().resolve(), interview_id)
    transcript_path = interview.artifact_root_path / "transcript.txt"
    if not transcript_path.is_file():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    if output_root is None:
        output_root = interview.artifact_root_path / "benchmarks" / interview.id
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    request = ReviewRequest(
        interview_id=interview.id,
        company=interview.company,
        role=interview.role,
        target_level=interview.target_level,
        round_type=interview.round_type,
        transcript_path=transcript_path,
    )

    rows: list[BenchmarkRow] = []
    for model in models:
        print(f"\nRunning {model} ...", flush=True)
        review = InterviewReviewService(OpenAIReviewEngine(model=model)).run(
            request,
            output_root / f"{_safe_model_name(model)}.json",
        )
        row = _comparison_row(review)
        rows.append(row)
        print(
            f"  {row['elapsed_seconds']:.1f}s | "
            f"{row['total_tokens']} tokens | "
            f"${row['estimated_cost_usd'] if row['estimated_cost_usd'] is not None else 'n/a'} | "
            f"{row['hiring_signal']} | confidence {row['confidence']:.0%}",
            flush=True,
        )

    comparison = {
        "interview_id": interview.id,
        "company": interview.company,
        "models": rows,
    }
    comparison_path = output_root / "comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return comparison_path, rows


def _parse_models(raw: str) -> list[str]:
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise argparse.ArgumentTypeError("At least one model is required")
    return models


def _print_summary(rows: Sequence[BenchmarkRow]) -> None:
    print("\nBenchmark summary")
    print("-" * 104)
    print(
        f"{'MODEL':<22} {'TIME':>8} {'TOKENS':>10} {'COST':>10} "
        f"{'SIGNAL':>18} {'CONF':>8} {'Q':>5} {'AVG':>7}"
    )
    print("-" * 104)
    for row in rows:
        elapsed = row["elapsed_seconds"]
        elapsed_text = f"{elapsed:.1f}s" if elapsed is not None else "—"
        cost = row["estimated_cost_usd"]
        cost_text = f"${cost:.4f}" if cost is not None else "—"
        avg = row["average_question_rating"]
        avg_text = f"{avg:.2f}" if avg is not None else "—"
        print(
            f"{str(row['model']):<22} {elapsed_text:>8} "
            f"{row['total_tokens']:>10,} {cost_text:>10} "
            f"{str(row['hiring_signal']):>18} "
            f"{row['confidence']:>7.0%} "
            f"{row['question_count']:>5} {avg_text:>7}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark AI review models against one existing transcript."
    )
    parser.add_argument("--interview", required=True, help="Interview UUID")
    parser.add_argument(
        "--models",
        type=_parse_models,
        default=list(DEFAULT_MODELS),
        help="Comma-separated model IDs",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite DB path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional benchmark output directory",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured")

    comparison_path, rows = run_benchmark(
        interview_id=args.interview,
        models=args.models,
        database_path=args.database,
        output_root=args.output,
    )
    _print_summary(rows)
    print(f"\nSaved comparison: {comparison_path}")


if __name__ == "__main__":
    main()
