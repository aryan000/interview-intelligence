from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from interview_intelligence.api.app import create_app


def test_health(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_interview(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    client = TestClient(create_app(tmp_path / "app.db"))

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "sequence_number": 1,
            "role": "Engineering Manager",
            "source_audio_path": str(source),
        },
    )

    assert created.status_code == 201
    interview_id = created.json()["id"]

    fetched = client.get(f"/api/v1/interviews/{interview_id}")

    assert fetched.status_code == 200
    assert fetched.json()["company"] == "PhonePe"
    assert fetched.json()["recruiter_or_interviewer"] == "Tushar"


def test_create_rejects_missing_audio(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "source_audio_path": str(tmp_path / "missing.wav"),
        },
    )

    assert response.status_code == 400


def test_missing_job_returns_404(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404
