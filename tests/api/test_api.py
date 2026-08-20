from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from interview_intelligence.api.app import create_app
from interview_intelligence.persistence.repositories import InterviewRepository


def test_health(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_interview(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))

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


def test_upload_interview_saves_audio_and_record(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))

    response = client.post(
        "/api/v1/interviews/upload",
        data={
            "company": "Navi",
            "recruiter_or_interviewer": "Sachin",
            "interview_datetime": "2026-08-21T16:15:00+05:30",
            "sequence_number": "1",
            "role": "Engineering Manager",
        },
        files={"audio": ("navi_round_1.mp3", b"fake audio", "audio/mpeg")},
    )

    assert response.status_code == 201
    saved_path = Path(response.json()["source_audio_path"])
    assert saved_path.is_file()
    assert saved_path.suffix == ".mp3"


def test_audio_endpoint_returns_source_audio(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio bytes")
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": datetime.now(UTC).isoformat(),
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    response = client.get(f"/api/v1/interviews/{interview_id}/audio")

    assert response.status_code == 200
    assert response.content == b"audio bytes"


def test_transcript_download_sets_attachment_filename(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")
    app = create_app(tmp_path / "app.db", tmp_path / "output")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "sequence_number": 1,
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir()
    (artifact_root / "transcript.txt").write_text("hello", encoding="utf-8")

    repository: InterviewRepository = app.state.interviews
    repository.set_artifact_root(
        repository.list_all()[0].id,
        str(artifact_root),
    )

    response = client.get(
        f"/api/v1/interviews/{interview_id}/transcript/download"
    )

    assert response.status_code == 200
    assert response.content == b"hello"
    assert "attachment" in response.headers["content-disposition"]


def test_list_interviews_returns_newest_first(tmp_path: Path) -> None:
    first_source = tmp_path / "first.wav"
    second_source = tmp_path / "second.wav"
    first_source.write_bytes(b"audio")
    second_source.write_bytes(b"audio")
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))

    first = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "source_audio_path": str(first_source),
        },
    )
    second = client.post(
        "/api/v1/interviews",
        json={
            "company": "Navi",
            "recruiter_or_interviewer": "Sachin",
            "interview_datetime": "2026-08-21T16:15:00+00:00",
            "source_audio_path": str(second_source),
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get("/api/v1/interviews")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["company"] == "Navi"
    assert payload[1]["company"] == "PhonePe"


def test_create_rejects_missing_audio(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))
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
    client = TestClient(create_app(tmp_path / "app.db", tmp_path / "output"))
    response = client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000001"
    )
    assert response.status_code == 404
