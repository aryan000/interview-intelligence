from datetime import UTC, datetime
from uuid import UUID

from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.models import InterviewRecord, ProcessingJobRecord


def _utcnow() -> datetime:
    return datetime.now(UTC)


class InterviewRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def save(self, interview: InterviewRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO interviews (
                    id, company, recruiter_or_interviewer, interview_datetime,
                    sequence_number, role, target_level, source_audio_path,
                    artifact_root_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    company = excluded.company,
                    recruiter_or_interviewer = excluded.recruiter_or_interviewer,
                    interview_datetime = excluded.interview_datetime,
                    sequence_number = excluded.sequence_number,
                    role = excluded.role,
                    target_level = excluded.target_level,
                    source_audio_path = excluded.source_audio_path,
                    artifact_root_path = excluded.artifact_root_path,
                    updated_at = excluded.updated_at
                """,
                (
                    str(interview.id),
                    interview.company,
                    interview.recruiter_or_interviewer,
                    interview.interview_datetime.isoformat(),
                    interview.sequence_number,
                    interview.role,
                    interview.target_level,
                    interview.source_audio_path,
                    interview.artifact_root_path,
                    interview.created_at.isoformat(),
                    interview.updated_at.isoformat(),
                ),
            )

    def get(self, interview_id: UUID) -> InterviewRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM interviews WHERE id = ?",
                (str(interview_id),),
            ).fetchone()

        if row is None:
            return None

        return InterviewRecord.model_validate(dict(row))

    def list_all(self) -> list[InterviewRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM interviews
                ORDER BY interview_datetime DESC, created_at DESC
                """
            ).fetchall()

        return [InterviewRecord.model_validate(dict(row)) for row in rows]

    def delete(self, interview_id: UUID) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM interviews WHERE id = ?",
                (str(interview_id),),
            )
        return cursor.rowcount > 0

    def set_artifact_root(self, interview_id: UUID, artifact_root_path: str) -> None:
        now = _utcnow()
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE interviews
                SET artifact_root_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (artifact_root_path, now.isoformat(), str(interview_id)),
            )


class ProcessingJobRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def save(self, job: ProcessingJobRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO processing_jobs (
                    id, interview_id, status, stage, progress_percent,
                    processed_audio_seconds, total_audio_seconds, message,
                    error_message, started_at, completed_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    stage = excluded.stage,
                    progress_percent = excluded.progress_percent,
                    processed_audio_seconds = excluded.processed_audio_seconds,
                    total_audio_seconds = excluded.total_audio_seconds,
                    message = excluded.message,
                    error_message = excluded.error_message,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    str(job.id),
                    str(job.interview_id),
                    job.status.value,
                    job.stage.value,
                    job.progress_percent,
                    job.processed_audio_seconds,
                    job.total_audio_seconds,
                    job.message,
                    job.error_message,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )

    def get(self, job_id: UUID) -> ProcessingJobRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM processing_jobs WHERE id = ?",
                (str(job_id),),
            ).fetchone()

        if row is None:
            return None

        return ProcessingJobRecord.model_validate(dict(row))

    def latest_for_interview(self, interview_id: UUID) -> ProcessingJobRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM processing_jobs
                WHERE interview_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(interview_id),),
            ).fetchone()

        if row is None:
            return None

        return ProcessingJobRecord.model_validate(dict(row))


    def list_active(self) -> list[ProcessingJobRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM processing_jobs
                WHERE status IN ('queued', 'running')
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [
            ProcessingJobRecord.model_validate(dict(row))
            for row in rows
        ]
