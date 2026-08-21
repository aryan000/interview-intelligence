import inspect
from pathlib import Path
from threading import Event
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
from interview_intelligence.transcription.runner import TranscriptionCancelled


class ProcessingCancelled(RuntimeError):
    pass


class ExistingInterviewProcessingCoordinator:
    """Process an already-persisted interview and an already-created job."""

    def __init__(
        self,
        pipeline: InterviewProcessingPipeline,
        interview_repository: InterviewRepository,
        job_service: ProcessingJobService,
        cancel_event: Event | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.interview_repository = interview_repository
        self.job_service = job_service
        self.cancel_event = cancel_event or Event()

    def run(
        self,
        interview_id: UUID,
        job_id: UUID,
    ) -> InterviewProcessingResult:
        interview = self._require_interview(interview_id)
        request = self._to_request(interview)
        source_metadata = self.pipeline.inspector.inspect(request.source_audio)

        try:
            self._raise_if_cancelled()

            self.job_service.start(job_id, "Inspecting recording")
            self.job_service.update_progress(
                job_id,
                JobStage.INSPECTION,
                progress_percent=2,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Recording inspected",
            )

            self._raise_if_cancelled()

            self.job_service.update_progress(
                job_id,
                JobStage.PREPROCESSING,
                progress_percent=5,
                processed_audio_seconds=0,
                total_audio_seconds=source_metadata.duration_seconds,
                message="Preparing canonical audio",
            )

            def report_progress(
                stage: JobStage,
                progress_percent: float,
                processed_audio_seconds: float,
                message: str,
            ) -> None:
                self._raise_if_cancelled()
                self.job_service.update_progress(
                    job_id,
                    stage,
                    progress_percent=progress_percent,
                    processed_audio_seconds=processed_audio_seconds,
                    total_audio_seconds=source_metadata.duration_seconds,
                    message=message,
                )

            process_parameters = inspect.signature(
                self.pipeline.process
            ).parameters

            if "cancel_event" in process_parameters:
                result = self.pipeline.process(
                    request,
                    progress_callback=report_progress,
                    cancel_event=self.cancel_event,
                )
            else:
                # Backward compatibility for tests or alternate pipelines that
                # implement the older process(request, progress_callback) contract.
                result = self.pipeline.process(
                    request,
                    progress_callback=report_progress,
                )

            self._raise_if_cancelled()

            self.interview_repository.set_artifact_root(
                interview.id,
                str(result.artifacts.root_dir),
            )
            self.interview_repository.set_processing_metrics(
                interview.id,
                transcription_seconds=result.transcription_seconds,
                diarization_seconds=result.diarization_seconds,
                total_processing_seconds=result.total_seconds,
            )
            self.job_service.complete(job_id)
            return result

        except (ProcessingCancelled, TranscriptionCancelled):
            self.job_service.cancel(
                job_id,
                "Processing stopped by user",
            )
            raise
        except Exception as exc:
            self.job_service.fail(job_id, str(exc))
            raise

    def _raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise ProcessingCancelled("Processing cancelled by user")

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
