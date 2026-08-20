from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from interview_intelligence.domain.enums import JobStage, JobStatus
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.models import (
    InterviewRecord,
    ProcessingJobRecord,
)
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


def test_round_trip_interview_and_job(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()

    now = datetime.now(UTC)
    interview = InterviewRecord(
        id=uuid4(),
        company="PhonePe",
        recruiter_or_interviewer="Tushar",
        interview_datetime=now,
        sequence_number=1,
        role="Engineering Manager",
        source_audio_path="/tmp/call.wav",
        created_at=now,
        updated_at=now,
    )

    interviews = InterviewRepository(database)
    interviews.save(interview)

    loaded_interview = interviews.get(interview.id)
    assert loaded_interview is not None
    assert loaded_interview.company == "PhonePe"

    job = ProcessingJobRecord(
        id=uuid4(),
        interview_id=interview.id,
        status=JobStatus.QUEUED,
        stage=JobStage.INSPECTION,
        progress_percent=0,
        processed_audio_seconds=0,
        total_audio_seconds=120,
        created_at=now,
        updated_at=now,
    )

    jobs = ProcessingJobRepository(database)
    jobs.save(job)

    loaded_job = jobs.get(job.id)
    assert loaded_job is not None
    assert loaded_job.total_audio_seconds == 120
