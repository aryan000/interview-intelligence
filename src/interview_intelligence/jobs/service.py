from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from interview_intelligence.domain.enums import JobStage, JobStatus
from interview_intelligence.jobs.events import JobProgressEvent
from interview_intelligence.persistence.models import ProcessingJobRecord
from interview_intelligence.persistence.repositories import ProcessingJobRepository

ProgressListener = Callable[[JobProgressEvent], None]


class ProcessingJobService:
    """State machine for durable processing-job progress."""

    _ORDER = {
        JobStage.INSPECTION: 0,
        JobStage.PREPROCESSING: 1,
        JobStage.VAD: 2,
        JobStage.TRANSCRIPTION: 3,
        JobStage.DIARIZATION: 4,
        JobStage.ALIGNMENT: 5,
        JobStage.EXPORT: 6,
        JobStage.CLOUD_SYNC: 7,
        JobStage.COMPLETED: 8,
    }

    def __init__(
        self,
        repository: ProcessingJobRepository,
        listener: ProgressListener | None = None,
    ) -> None:
        self.repository = repository
        self.listener = listener

    def create(
        self,
        interview_id: UUID,
        total_audio_seconds: float = 0,
    ) -> ProcessingJobRecord:
        now = datetime.now(UTC)
        job = ProcessingJobRecord(
            id=uuid4(),
            interview_id=interview_id,
            status=JobStatus.QUEUED,
            stage=JobStage.INSPECTION,
            progress_percent=0,
            processed_audio_seconds=0,
            total_audio_seconds=total_audio_seconds,
            created_at=now,
            updated_at=now,
        )
        self.repository.save(job)
        self._emit(job)
        return job

    def start(
        self,
        job_id: UUID,
        message: str | None = None,
    ) -> ProcessingJobRecord:
        job = self._require(job_id)
        now = datetime.now(UTC)
        updated = job.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "started_at": job.started_at or now,
                "updated_at": now,
                "message": message,
            }
        )
        self.repository.save(updated)
        self._emit(updated)
        return updated

    def update_progress(
        self,
        job_id: UUID,
        stage: JobStage,
        progress_percent: float,
        processed_audio_seconds: float,
        total_audio_seconds: float,
        message: str | None = None,
    ) -> ProcessingJobRecord:
        job = self._require(job_id)
        self._validate_transition(job.stage, stage)

        now = datetime.now(UTC)
        updated = job.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "stage": stage,
                "progress_percent": progress_percent,
                "processed_audio_seconds": processed_audio_seconds,
                "total_audio_seconds": total_audio_seconds,
                "message": message,
                "updated_at": now,
            }
        )
        self.repository.save(updated)
        self._emit(updated)
        return updated

    def complete(self, job_id: UUID) -> ProcessingJobRecord:
        job = self._require(job_id)
        now = datetime.now(UTC)
        updated = job.model_copy(
            update={
                "status": JobStatus.COMPLETED,
                "stage": JobStage.COMPLETED,
                "progress_percent": 100.0,
                "processed_audio_seconds": job.total_audio_seconds,
                "completed_at": now,
                "updated_at": now,
                "message": "Completed",
            }
        )
        self.repository.save(updated)
        self._emit(updated)
        return updated

    def fail(
        self,
        job_id: UUID,
        error_message: str,
    ) -> ProcessingJobRecord:
        job = self._require(job_id)
        now = datetime.now(UTC)
        updated = job.model_copy(
            update={
                "status": JobStatus.FAILED,
                "error_message": error_message,
                "completed_at": now,
                "updated_at": now,
                "message": "Failed",
            }
        )
        self.repository.save(updated)
        self._emit(updated)
        return updated

    def _require(self, job_id: UUID) -> ProcessingJobRecord:
        job = self.repository.get(job_id)
        if job is None:
            raise KeyError(f"Processing job not found: {job_id}")
        return job

    def _validate_transition(
        self,
        current: JobStage,
        target: JobStage,
    ) -> None:
        if self._ORDER[target] < self._ORDER[current]:
            raise ValueError(
                f"Cannot move processing stage backwards: "
                f"{current.value} -> {target.value}"
            )

    def _emit(self, job: ProcessingJobRecord) -> None:
        if self.listener is None:
            return
        self.listener(
            JobProgressEvent(
                job_id=job.id,
                interview_id=job.interview_id,
                status=job.status,
                stage=job.stage,
                progress_percent=job.progress_percent,
                processed_audio_seconds=job.processed_audio_seconds,
                total_audio_seconds=job.total_audio_seconds,
                message=job.message,
                occurred_at=job.updated_at,
            )
        )
