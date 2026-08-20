import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import PlainTextResponse

from interview_intelligence.api.dependencies import (
    background_manager,
    broker,
    interviews,
    jobs,
)
from interview_intelligence.api.schemas import (
    InterviewCreateRequest,
    InterviewResponse,
    JobResponse,
    ProcessInterviewResponse,
    TranscriptResponse,
)
from interview_intelligence.domain.enums import JobStatus
from interview_intelligence.jobs.broker import JobEventBroker
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.models import InterviewRecord
from interview_intelligence.persistence.repositories import ProcessingJobRepository


def _to_interview_response(record: InterviewRecord) -> InterviewResponse:
    return InterviewResponse(
        id=record.id,
        company=record.company,
        recruiter_or_interviewer=record.recruiter_or_interviewer,
        interview_datetime=record.interview_datetime,
        sequence_number=record.sequence_number,
        role=record.role,
        target_level=record.target_level,
        source_audio_path=record.source_audio_path,
        artifact_root_path=record.artifact_root_path,
    )


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post(
        "/interviews",
        response_model=InterviewResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_interview(
        payload: InterviewCreateRequest,
        request: Request,
    ) -> InterviewResponse:
        source = Path(payload.source_audio_path).expanduser().resolve()
        if not source.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_audio_path does not exist",
            )

        now = datetime.now(UTC)
        record = InterviewRecord(
            company=payload.company,
            recruiter_or_interviewer=payload.recruiter_or_interviewer,
            interview_datetime=payload.interview_datetime,
            sequence_number=payload.sequence_number,
            role=payload.role,
            target_level=payload.target_level,
            source_audio_path=str(source),
            created_at=now,
            updated_at=now,
        )
        interviews(request).save(record)
        return _to_interview_response(record)

    @router.get(
        "/interviews/{interview_id}",
        response_model=InterviewResponse,
    )
    def get_interview(
        interview_id: UUID,
        request: Request,
    ) -> InterviewResponse:
        record = interviews(request).get(interview_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )
        return _to_interview_response(record)

    @router.post(
        "/interviews/{interview_id}/process",
        response_model=ProcessInterviewResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def process_interview(
        interview_id: UUID,
        request: Request,
    ) -> ProcessInterviewResponse:
        record = interviews(request).get(interview_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        job_repository = jobs(request)
        latest = job_repository.latest_for_interview(interview_id)
        if latest is not None and latest.status in {
            JobStatus.QUEUED,
            JobStatus.RUNNING,
        }:
            return ProcessInterviewResponse(
                job_id=latest.id,
                interview_id=interview_id,
                status=latest.status,
            )

        event_broker = broker(request)
        event_broker.bind_loop(asyncio.get_running_loop())

        source_path = Path(record.source_audio_path)
        from interview_intelligence.audio.inspector import FFprobeAudioInspector

        duration = FFprobeAudioInspector().inspect(source_path).duration_seconds
        job_service = ProcessingJobService(
            job_repository,
            listener=event_broker.publish_threadsafe,
        )
        job = job_service.create(
            interview_id,
            total_audio_seconds=duration,
        )

        try:
            background_manager(request).start(interview_id, job.id)
        except RuntimeError as exc:
            job_service.fail(job.id, str(exc))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        return ProcessInterviewResponse(
            job_id=job.id,
            interview_id=interview_id,
            status=job.status,
        )

    @router.get(
        "/jobs/{job_id}",
        response_model=JobResponse,
    )
    def get_job(job_id: UUID, request: Request) -> JobResponse:
        job = jobs(request).get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found",
            )
        return JobResponse(
            id=job.id,
            interview_id=job.interview_id,
            status=job.status,
            stage=job.stage,
            progress_percent=job.progress_percent,
            processed_audio_seconds=job.processed_audio_seconds,
            total_audio_seconds=job.total_audio_seconds,
            message=job.message,
            error_message=job.error_message,
        )

    @router.websocket("/jobs/{job_id}/events")
    async def job_events(websocket: WebSocket, job_id: UUID) -> None:
        await websocket.accept()

        event_broker = cast(JobEventBroker, websocket.app.state.job_event_broker)
        event_broker.bind_loop(asyncio.get_running_loop())
        job_repository = cast(ProcessingJobRepository, websocket.app.state.jobs)
        queue = event_broker.subscribe(job_id)

        try:
            current = job_repository.get(job_id)
            if current is None:
                await websocket.send_json({"error": "Processing job not found"})
                await websocket.close(code=1008)
                return

            await websocket.send_json(
                {
                    "job_id": str(current.id),
                    "interview_id": str(current.interview_id),
                    "status": current.status.value,
                    "stage": current.stage.value,
                    "progress_percent": current.progress_percent,
                    "processed_audio_seconds": current.processed_audio_seconds,
                    "total_audio_seconds": current.total_audio_seconds,
                    "message": current.message,
                    "occurred_at": current.updated_at.isoformat(),
                }
            )

            if current.status in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            }:
                await websocket.close(code=1000)
                return

            while True:
                event = await queue.get()
                await websocket.send_json(event.model_dump(mode="json"))

                if event.status in {
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                }:
                    await websocket.close(code=1000)
                    break

        except WebSocketDisconnect:
            pass
        finally:
            event_broker.unsubscribe(job_id, queue)

    @router.get(
        "/interviews/{interview_id}/transcript",
        response_model=TranscriptResponse,
    )
    def get_transcript(
        interview_id: UUID,
        request: Request,
    ) -> TranscriptResponse:
        record = interviews(request).get(interview_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )
        if record.artifact_root_path is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interview has not been processed",
            )

        transcript_path = Path(record.artifact_root_path) / "transcript.txt"
        if not transcript_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript artifact not found",
            )

        return TranscriptResponse(
            interview_id=record.id,
            transcript=transcript_path.read_text(encoding="utf-8"),
        )

    @router.get(
        "/interviews/{interview_id}/transcript.txt",
        response_class=PlainTextResponse,
    )
    def get_transcript_text(
        interview_id: UUID,
        request: Request,
    ) -> str:
        record = interviews(request).get(interview_id)
        if record is None or record.artifact_root_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found",
            )
        transcript_path = Path(record.artifact_root_path) / "transcript.txt"
        if not transcript_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found",
            )
        return transcript_path.read_text(encoding="utf-8")

    return router
