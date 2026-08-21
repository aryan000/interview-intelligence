from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from interview_intelligence.api.app import create_app
from interview_intelligence.persistence.repositories import InterviewRepository


def test_interview_round_type_and_metadata_can_be_updated(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    app = create_app(tmp_path / "app.db", tmp_path / "output")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "Microsoft",
            "recruiter_or_interviewer": "Alex",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "sequence_number": 2,
            "role": "Engineering Manager",
            "round_type": "HLD",
            "source_audio_path": str(source),
        },
    )

    assert created.status_code == 201
    interview_id = created.json()["id"]
    assert created.json()["round_type"] == "HLD"

    updated = client.patch(
        f"/api/v1/interviews/{interview_id}",
        json={
            "recruiter_or_interviewer": "Jordan",
            "round_type": "Leadership",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["recruiter_or_interviewer"] == "Jordan"
    assert updated.json()["round_type"] == "Leadership"

    fetched = client.get(f"/api/v1/interviews/{interview_id}")
    assert fetched.status_code == 200
    assert fetched.json()["recruiter_or_interviewer"] == "Jordan"
    assert fetched.json()["round_type"] == "Leadership"


def test_processing_metrics_are_returned_in_library_response(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    app = create_app(tmp_path / "app.db", tmp_path / "output")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "Navi",
            "recruiter_or_interviewer": "Interviewer",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    repository: InterviewRepository = app.state.interviews
    interview = repository.list_all()[0]
    repository.set_processing_metrics(
        interview.id,
        transcription_seconds=742.5,
        diarization_seconds=153.2,
        total_processing_seconds=913.4,
    )

    listed = client.get("/api/v1/interviews")

    assert listed.status_code == 200
    record = next(
        item for item in listed.json()
        if item["id"] == interview_id
    )
    assert record["transcription_seconds"] == 742.5
    assert record["diarization_seconds"] == 153.2
    assert record["total_processing_seconds"] == 913.4
