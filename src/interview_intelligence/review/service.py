import json
import time
from datetime import UTC, datetime
from pathlib import Path

from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import (
    InterviewReview,
    ReviewAnalysisMetadata,
    ReviewRequest,
)


class InterviewReviewService:
    """Run a pluggable review engine and persist a stable review artifact."""

    def __init__(self, engine: InterviewReviewEngine) -> None:
        self.engine = engine

    def run(
        self,
        request: ReviewRequest,
        output_path: Path,
    ) -> InterviewReview:
        transcript_path = request.transcript_path.expanduser().resolve()
        if not transcript_path.is_file():
            raise FileNotFoundError(f"Transcript not found: {transcript_path}")

        transcript = transcript_path.read_text(encoding="utf-8")
        if not transcript.strip():
            raise ValueError("Transcript is empty")

        started_at = datetime.now(UTC)
        started = time.perf_counter()
        review = self.engine.review(request, transcript)
        completed_at = datetime.now(UTC)

        review = review.model_copy(
            update={
                "analysis": ReviewAnalysisMetadata(
                    started_at=started_at,
                    completed_at=completed_at,
                    elapsed_seconds=time.perf_counter() - started,
                )
            }
        )

        resolved_output = output_path.expanduser().resolve()
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(
            json.dumps(review.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        return review
