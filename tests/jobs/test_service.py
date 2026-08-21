from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from interview_intelligence.domain.enums import JobStage, JobStatus
from interview_intelligence.jobs.events import JobProgressEvent
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.models import InterviewRecord
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


@dataclass(frozen=True)
class ServiceFixture:
    service: ProcessingJobService
    interview_id: UUID


def build_service(
    tmp_path: Path,
    events: list[JobProgressEvent],
) -> ServiceFixture:
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()

    now = datetime.now(UTC)
    interview = InterviewRecord(
        id=uuid4(),
        company="PhonePe",
        recruiter_or_interviewer="Tushar",
        interview_datetime=now,
        sequence_number=1,
        source_audio_path="/tmp/call.wav",
        created_at=now,
        updated_at=now,
    )
    InterviewRepository(database).save(interview)

    return ServiceFixture(
        service=ProcessingJobService(
            ProcessingJobRepository(database),
            listener=events.append,
        ),
        interview_id=interview.id,
    )


def test_job_progress_is_persisted_and_emitted(tmp_path: Path) -> None:
    events: list[JobProgressEvent] = []
    fixture = build_service(tmp_path, events)

    job = fixture.service.create(fixture.interview_id, total_audio_seconds=120)
    fixture.service.start(job.id, "Starting")
    updated = fixture.service.update_progress(
        job.id,
        JobStage.TRANSCRIPTION,
        progress_percent=50,
        processed_audio_seconds=60,
        total_audio_seconds=120,
        message="Transcribing",
    )
    completed = fixture.service.complete(job.id)

    assert updated.status == JobStatus.RUNNING
    assert updated.stage == JobStage.TRANSCRIPTION
    assert completed.status == JobStatus.COMPLETED
    assert completed.progress_percent == 100
    assert len(events) == 4


def test_job_stage_cannot_move_backwards(tmp_path: Path) -> None:
    events: list[JobProgressEvent] = []
    fixture = build_service(tmp_path, events)

    job = fixture.service.create(fixture.interview_id, total_audio_seconds=120)
    fixture.service.update_progress(
        job.id,
        JobStage.DIARIZATION,
        progress_percent=80,
        processed_audio_seconds=120,
        total_audio_seconds=120,
    )

    with pytest.raises(ValueError, match="backwards"):
        fixture.service.update_progress(
            job.id,
            JobStage.TRANSCRIPTION,
            progress_percent=50,
            processed_audio_seconds=60,
            total_audio_seconds=120,
        )



def test_cancel_marks_job_terminal(tmp_path: Path) -> None:
    events: list[JobProgressEvent] = []
    fixture = build_service(tmp_path, events)

    job = fixture.service.create(
        fixture.interview_id,
        total_audio_seconds=120,
    )
    fixture.service.start(job.id, "Processing")

    cancelled = fixture.service.cancel(job.id)

    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.completed_at is not None
    assert cancelled.message == "Processing stopped"
