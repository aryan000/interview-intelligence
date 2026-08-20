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



def test_latest_interview_job_returns_persisted_timestamps(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")
    app = create_app(tmp_path / "app.db", tmp_path / "output")
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
    interview_id = created.json()["id"]

    from interview_intelligence.jobs.service import ProcessingJobService

    service = ProcessingJobService(app.state.jobs)
    job = service.create(
        app.state.interviews.list_all()[0].id,
        total_audio_seconds=120,
    )
    service.start(job.id, "Starting")

    response = client.get(f"/api/v1/interviews/{interview_id}/jobs/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(job.id)
    assert payload["status"] == "running"
    assert payload["started_at"] is not None
    assert payload["updated_at"] is not None



def test_delete_interview_removes_database_row_and_managed_files(tmp_path: Path) -> None:
    app = create_app(tmp_path / "app.db", tmp_path / "recordings")
    client = TestClient(app)

    uploaded = client.post(
        "/api/v1/interviews/upload",
        data={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "sequence_number": "1",
        },
        files={"audio": ("round.mp3", b"managed audio", "audio/mpeg")},
    )
    assert uploaded.status_code == 201
    interview_id = uploaded.json()["id"]
    source_path = Path(uploaded.json()["source_audio_path"])
    assert source_path.is_file()

    artifact_root = tmp_path / "recordings" / "PhonePe" / "artifact"
    artifact_root.mkdir(parents=True)
    (artifact_root / "transcript.txt").write_text("hello", encoding="utf-8")

    interview = app.state.interviews.get(interview_id)
    assert interview is not None
    app.state.interviews.set_artifact_root(interview.id, str(artifact_root))

    response = client.delete(f"/api/v1/interviews/{interview_id}")

    assert response.status_code == 204
    assert app.state.interviews.get(interview.id) is None
    assert not source_path.exists()
    assert not artifact_root.exists()


def test_delete_interview_preserves_external_source_audio(tmp_path: Path) -> None:
    external_audio = tmp_path / "external.wav"
    external_audio.write_bytes(b"original audio")

    app = create_app(tmp_path / "app.db", tmp_path / "recordings")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "source_audio_path": str(external_audio),
        },
    )
    assert created.status_code == 201

    response = client.delete(
        f"/api/v1/interviews/{created.json()['id']}"
    )

    assert response.status_code == 204
    assert external_audio.is_file()


def test_delete_interview_rejects_active_processing_job(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")

    app = create_app(tmp_path / "app.db", tmp_path / "recordings")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    from interview_intelligence.jobs.service import ProcessingJobService

    interview = app.state.interviews.get(interview_id)
    assert interview is not None

    service = ProcessingJobService(app.state.jobs)
    job = service.create(interview.id, total_audio_seconds=120)
    service.start(job.id, "Processing")

    response = client.delete(f"/api/v1/interviews/{interview_id}")

    assert response.status_code == 409
    assert app.state.interviews.get(interview.id) is not None



def test_list_interviews_includes_duration_from_latest_job(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"audio")
    app = create_app(tmp_path / "app.db", tmp_path / "recordings")
    client = TestClient(app)

    created = client.post(
        "/api/v1/interviews",
        json={
            "company": "PhonePe",
            "recruiter_or_interviewer": "Tushar",
            "interview_datetime": "2026-07-30T12:00:00+00:00",
            "source_audio_path": str(source),
        },
    )
    interview_id = created.json()["id"]

    from interview_intelligence.jobs.service import ProcessingJobService

    interview = app.state.interviews.get(interview_id)
    assert interview is not None

    service = ProcessingJobService(app.state.jobs)
    service.create(interview.id, total_audio_seconds=4771.99745)

    response = client.get("/api/v1/interviews")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["duration_seconds"] == 4771.99745
