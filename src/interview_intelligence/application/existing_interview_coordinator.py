from pathlib import Path
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


class ExistingInterviewProcessingCoordinator:
    """Process an already-persisted interview and an already-created job."""

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
        interview_id: UUID,
        job_id: UUID,
    ) -> InterviewProcessingResult:
        interview = self._require_interview(interview_id)
        request = self._to_request(interview)
        source_metadata = self.pipeline.inspector.inspect(request.source_audio)

        try:
            self.job_service.start(job_id, "Inspecting recording")
            self.job_service.update_progress(
                job_id,
                JobStage.INSPECTION,
                progress_percent=2,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Recording inspected",
            )
            self.job_service.update_progress(
                job_id,
                JobStage.PREPROCESSING,
                progress_percent=5,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Preparing canonical audio",
            )

            result = self.pipeline.process(request)

            self.job_service.update_progress(
                job_id,
                JobStage.TRANSCRIPTION,
                progress_percent=70,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Transcription complete",
            )
            self.job_service.update_progress(
                job_id,
                JobStage.DIARIZATION,
                progress_percent=88,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Speaker diarization complete",
            )
            self.job_service.update_progress(
                job_id,
                JobStage.ALIGNMENT,
                progress_percent=94,
                processed_audio_seconds=result.prepared_metadata.duration_seconds,
                total_audio_seconds=result.prepared_metadata.duration_seconds,
                message="Speaker alignment complete",
            )
            self.job_service.update_progress(
                job_id,
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
            self.job_service.complete(job_id)
            return result

        except Exception as exc:
            self.job_service.fail(job_id, str(exc))
            raise

    def _require_interview(self, interview_id: UUID) -> InterviewRecord:
        interview = self.interview_repository.get(interview_id)
        if interview is None:
            raise KeyError(f"Interview not found: {interview_id}")
        return interview

    @staticmethod
    def _to_request(interview: InterviewRecord) -> InterviewProcessingRequest:
        return InterviewProcessingRequest(
            source_audio=Path(interview.source_audio_path),
            company=interview.company,
            recruiter_or_interviewer=interview.recruiter_or_interviewer,
            sequence_number=interview.sequence_number,
            interview_datetime=interview.interview_datetime,
            role=interview.role,
            target_level=interview.target_level,
            num_speakers=2,
        )
