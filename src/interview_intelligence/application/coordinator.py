from datetime import UTC, datetime
from uuid import UUID

from interview_intelligence.domain.enums import JobStage
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.models import InterviewRecord
from interview_intelligence.persistence.repositories import InterviewRepository
from interview_intelligence.pipeline.models import (
    InterviewProcessingRequest,
    InterviewProcessingResult,
)
from interview_intelligence.pipeline.processor import InterviewProcessingPipeline


class InterviewProcessingCoordinator:
    """Persist interview/job state around the end-to-end processing pipeline."""

    def __init__(
        self,
        pipeline: InterviewProcessingPipeline,
        interview_repository: InterviewRepository,
        job_service: ProcessingJobService,
    ) -> None:
        self.pipeline = pipeline
        self.interview_repository = interview_repository
        self.job_service = job_service

    def run(
        self,
        request: InterviewProcessingRequest,
    ) -> tuple[UUID, InterviewProcessingResult]:
        now = datetime.now(UTC)
        interview = InterviewRecord(
            company=request.company,
            recruiter_or_interviewer=request.recruiter_or_interviewer,
            interview_datetime=request.interview_datetime,
            sequence_number=request.sequence_number,
            role=request.role,
            target_level=request.target_level,
            source_audio_path=str(request.source_audio),
            created_at=now,
            updated_at=now,
        )
        self.interview_repository.save(interview)

        source_metadata = self.pipeline.inspector.inspect(request.source_audio)
        job = self.job_service.create(
            interview.id,
            total_audio_seconds=source_metadata.duration_seconds,
        )

        try:
            self.job_service.start(job.id, "Inspecting recording")
            self.job_service.update_progress(
                job.id,
                JobStage.INSPECTION,
                progress_percent=2,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Recording inspected",
            )
            self.job_service.update_progress(
                job.id,
                JobStage.PREPROCESSING,
                progress_percent=5,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Preparing canonical audio",
            )

            result = self.pipeline.process(request)

            self.job_service.update_progress(
                job.id,
                JobStage.TRANSCRIPTION,
                progress_percent=70,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Transcription complete",
            )
            self.job_service.update_progress(
                job.id,
                JobStage.DIARIZATION,
                progress_percent=88,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Speaker diarization complete",
            )
            self.job_service.update_progress(
                job.id,
                JobStage.ALIGNMENT,
                progress_percent=94,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Speaker alignment complete",
            )
            self.job_service.update_progress(
                job.id,
                JobStage.EXPORT,
                progress_percent=99,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Artifacts exported",
            )

            self.interview_repository.set_artifact_root(
                interview.id,
                str(result.artifacts.root_dir),
            )
            self.job_service.complete(job.id)

            return job.id, result

        except Exception as exc:
            self.job_service.fail(job.id, str(exc))
            raise
