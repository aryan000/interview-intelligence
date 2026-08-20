from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from interview_intelligence.api.app import create_app
from interview_intelligence.persistence.repositories import InterviewRepository
from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    ReviewRequest,
)


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
            model="stub-review-model",
            overall_summary="Strong decomposition with some prioritization gaps.",
            hiring_signal=HiringSignal.HIRE,
            confidence=0.85,
            strengths=["Clear decomposition"],
            concerns=["Prioritization could be sharper"],
        )


def test_review_api_creates_and_reads_persisted_review(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    app = create_app(tmp_path / "app.db", tmp_path / "output")
    app.state.review_engine = StubReviewEngine()
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "role": "Engineering Manager",
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir()
    (artifact_root / "transcript.txt").write_text(
        "[00:00:00 -> 00:00:05] Interviewer: Design a payment system.\n"
        "[00:00:06 -> 00:00:20] Candidate: I would start with requirements.\n",
        encoding="utf-8",
    )

    repository: InterviewRepository = app.state.interviews
    interview = repository.get(interview_id)
    assert interview is not None
    repository.set_artifact_root(interview.id, str(artifact_root))

    reviewed = client.post(f"/api/v1/interviews/{interview_id}/review")

    assert reviewed.status_code == 200
    assert reviewed.json()["hiring_signal"] == "hire"
    assert (artifact_root / "review.json").is_file()

    fetched = client.get(f"/api/v1/interviews/{interview_id}/review")

    assert fetched.status_code == 200
    assert fetched.json()["provider"] == "stub"


def test_review_api_requires_processed_interview(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    app = create_app(tmp_path / "app.db", tmp_path / "output")
    app.state.review_engine = StubReviewEngine()
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "source_audio_path": str(source),
        },
    )

    response = client.post(
        f"/api/v1/interviews/{created.json()['id']}/review"
    )

    assert response.status_code == 409
