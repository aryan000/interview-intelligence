from pathlib import Path

from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    ReviewRequest,
    ReviewUsage,
)
from interview_intelligence.review.pricing import estimate_cost_usd
from interview_intelligence.review.service import InterviewReviewService


class StubEngine(InterviewReviewEngine):
    def review(
        self,
        request: ReviewRequest,
        transcript: str,
    ) -> InterviewReview:
        return InterviewReview(
            interview_id=request.interview_id,
            provider="stub",
            model="stub-model",
            overall_summary="Summary",
            hiring_signal=HiringSignal.MIXED,
            confidence=0.7,
            usage=ReviewUsage(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            ),
        )


def test_review_service_persists_analysis_timing(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("Interview transcript", encoding="utf-8")
    output = tmp_path / "review.json"

    result = InterviewReviewService(StubEngine()).run(
        ReviewRequest(
            interview_id="abc",
            company="Example",
            transcript_path=transcript,
        ),
        output,
    )

    assert result.analysis is not None
    assert result.analysis.elapsed_seconds >= 0
    assert result.analysis.completed_at >= result.analysis.started_at
    assert output.is_file()
    persisted = InterviewReview.model_validate_json(
        output.read_text(encoding="utf-8")
    )
    assert persisted.analysis is not None


def test_gpt_56_sol_cost_uses_cached_and_output_rates() -> None:
    usage = ReviewUsage(
        input_tokens=10_000,
        cached_input_tokens=2_000,
        cache_write_tokens=1_000,
        output_tokens=2_000,
        reasoning_tokens=500,
        total_tokens=12_000,
    )

    cost, basis = estimate_cost_usd("gpt-5.6-sol", usage)

    # 7k normal input @ $5/M + 2k cached @ $0.50/M
    # + 1k cache write @ $6.25/M + 2k output @ $30/M.
    assert cost == 0.10225
    assert basis is not None
