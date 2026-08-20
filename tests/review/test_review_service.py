from pathlib import Path

from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    ReviewRequest,
)
from interview_intelligence.review.service import InterviewReviewService


class StubReviewEngine(InterviewReviewEngine):
    def review(
        self,
        request: ReviewRequest,
        transcript: str,
    ) -> InterviewReview:
        assert "Interviewer" in transcript
        return InterviewReview(
            interview_id=request.interview_id,
            provider="stub",
            model="stub-model",
            overall_summary="Structured review",
            hiring_signal=HiringSignal.MIXED,
            confidence=0.7,
        )


def test_review_service_reads_transcript_and_writes_review_json(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text(
        "[00:00:00 -> 00:00:05] Interviewer: Tell me about yourself.\n",
        encoding="utf-8",
    )

    output = tmp_path / "review.json"

    result = InterviewReviewService(StubReviewEngine()).run(
        ReviewRequest(
            interview_id="abc",
            company="PhonePe",
            role="Engineering Manager",
            transcript_path=transcript,
        ),
        output,
    )

    assert result.interview_id == "abc"
    assert output.is_file()
    assert '"hiring_signal": "mixed"' in output.read_text(encoding="utf-8")


def test_review_service_rejects_empty_transcript(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("", encoding="utf-8")

    service = InterviewReviewService(StubReviewEngine())

    try:
        service.run(
            ReviewRequest(
                interview_id="abc",
                company="PhonePe",
                transcript_path=transcript,
            ),
            tmp_path / "review.json",
        )
    except ValueError as exc:
        assert str(exc) == "Transcript is empty"
    else:
        raise AssertionError("Expected ValueError")
