import asyncio
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, PlainTextResponse

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
from interview_intelligence.persistence.models import InterviewRecord, ProcessingJobRecord
from interview_intelligence.persistence.repositories import ProcessingJobRepository

_ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac"}


def _to_interview_response(
    record: InterviewRecord,
    duration_seconds: float | None = None,
) -> InterviewResponse:
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
        duration_seconds=duration_seconds,
    )


def _require_interview(
    interview_id: UUID,
    request: Request,
) -> InterviewRecord:
    record = interviews(request).get(interview_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )
    return record


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _delete_managed_path(path: Path, root: Path) -> None:
    if not _is_within(path, root):
        return

    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()


STALE_JOB_GRACE_PERIOD = timedelta(seconds=30)


def _reconcile_stale_job(
    interview_id: UUID,
    request: Request,
) -> ProcessingJobRecord | None:
    repository = jobs(request)
    latest = repository.latest_for_interview(interview_id)

    if latest is None:
        return None

    has_active_worker = background_manager(request).is_active(interview_id)
    job_age = datetime.now(UTC) - latest.updated_at

    if (
        latest.status in {JobStatus.QUEUED, JobStatus.RUNNING}
        and not has_active_worker
        and job_age >= STALE_JOB_GRACE_PERIOD
    ):
        service = ProcessingJobService(
            repository,
            listener=broker(request).publish_threadsafe,
        )
        latest = service.fail(
            latest.id,
            "Processing was interrupted because the backend stopped or restarted.",
        )

    return latest


def _to_job_response(job: ProcessingJobRecord) -> JobResponse:
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
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
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

    @router.post(
        "/interviews/upload",
        response_model=InterviewResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_interview(
        request: Request,
        audio: Annotated[UploadFile, File()],
        company: Annotated[str, Form()],
        recruiter_or_interviewer: Annotated[str, Form()],
        interview_datetime: Annotated[datetime, Form()],
        sequence_number: Annotated[int, Form()] = 1,
        role: Annotated[str | None, Form()] = None,
        target_level: Annotated[str | None, Form()] = None,
    ) -> InterviewResponse:
        suffix = Path(audio.filename or "").suffix.lower()
        if suffix not in _ALLOWED_AUDIO_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported audio format. Use MP3, WAV, M4A, or AAC.",
            )

        upload_dir = cast(Path, request.app.state.upload_dir)
        destination = upload_dir / f"{uuid4().hex}{suffix}"

        try:
            with destination.open("wb") as output:
                shutil.copyfileobj(audio.file, output)
        finally:
            await audio.close()

        now = datetime.now(UTC)
        record = InterviewRecord(
            company=company.strip(),
            recruiter_or_interviewer=recruiter_or_interviewer.strip(),
            interview_datetime=interview_datetime,
            sequence_number=sequence_number,
            role=role.strip() if role else None,
            target_level=target_level.strip() if target_level else None,
            source_audio_path=str(destination),
            created_at=now,
            updated_at=now,
        )
        interviews(request).save(record)
        return _to_interview_response(record)

    @router.get(
        "/interviews",
        response_model=list[InterviewResponse],
    )
    def list_interviews(request: Request) -> list[InterviewResponse]:
        responses: list[InterviewResponse] = []

        for record in interviews(request).list_all():
            latest_job = jobs(request).latest_for_interview(record.id)
            duration_seconds = (
                latest_job.total_audio_seconds
                if latest_job is not None
                else None
            )
            responses.append(
                _to_interview_response(
                    record,
                    duration_seconds=duration_seconds,
                )
            )

        return responses

    @router.get(
        "/interviews/{interview_id}",
        response_model=InterviewResponse,
    )
    def get_interview(
        interview_id: UUID,
        request: Request,
    ) -> InterviewResponse:
        return _to_interview_response(_require_interview(interview_id, request))

    @router.delete(
        "/interviews/{interview_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_interview(
        interview_id: UUID,
        request: Request,
    ) -> None:
        record = _require_interview(interview_id, request)

        latest = jobs(request).latest_for_interview(interview_id)
        if latest is not None and latest.status in {
            JobStatus.QUEUED,
            JobStatus.RUNNING,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an interview while processing is active",
            )

        recordings_root = cast(Path, request.app.state.recordings_root)
        upload_dir = cast(Path, request.app.state.upload_dir)

        artifact_root = (
            Path(record.artifact_root_path)
            if record.artifact_root_path is not None
            else None
        )
        source_audio = Path(record.source_audio_path)

        if not interviews(request).delete(interview_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        if artifact_root is not None:
            _delete_managed_path(artifact_root, recordings_root)

        # Only remove uploaded copies managed by this application.
        # External/original recordings are intentionally left untouched.
        _delete_managed_path(source_audio, upload_dir)

    @router.post(
        "/interviews/{interview_id}/process",
        response_model=ProcessInterviewResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def process_interview(
        interview_id: UUID,
        request: Request,
    ) -> ProcessInterviewResponse:
        record = _require_interview(interview_id, request)

        job_repository = jobs(request)
        latest = _reconcile_stale_job(interview_id, request)
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

    @router.post(
        "/interviews/{interview_id}/process/cancel",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def cancel_processing(
        interview_id: UUID,
        request: Request,
    ) -> JobResponse:
        _require_interview(interview_id, request)

        repository = jobs(request)
        latest = _reconcile_stale_job(interview_id, request)
        if latest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found",
            )

        if latest.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return _to_job_response(latest)

        manager = background_manager(request)
        service = ProcessingJobService(
            repository,
            listener=broker(request).publish_threadsafe,
        )

        if not manager.request_cancel(interview_id):
            interrupted = service.fail(
                latest.id,
                "Processing was interrupted because no active worker was found.",
            )
            return _to_job_response(interrupted)

        requested = service.request_cancel(
            latest.id,
            "Stopping processing after the current ML step",
        )
        return _to_job_response(requested)

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
        return _to_job_response(job)

    @router.get(
        "/interviews/{interview_id}/jobs/latest",
        response_model=JobResponse,
    )
    def get_latest_interview_job(
        interview_id: UUID,
        request: Request,
    ) -> JobResponse:
        _require_interview(interview_id, request)
        job = _reconcile_stale_job(interview_id, request)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found",
            )
        return _to_job_response(job)

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
        "/interviews/{interview_id}/audio",
        response_class=FileResponse,
    )
    def get_audio(
        interview_id: UUID,
        request: Request,
    ) -> FileResponse:
        record = _require_interview(interview_id, request)
        audio_path = Path(record.source_audio_path)

        if not audio_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        return FileResponse(audio_path)

    @router.get(
        "/interviews/{interview_id}/transcript",
        response_model=TranscriptResponse,
    )
    def get_transcript(
        interview_id: UUID,
        request: Request,
    ) -> TranscriptResponse:
        record = _require_interview(interview_id, request)
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
        record = _require_interview(interview_id, request)
        if record.artifact_root_path is None:
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

    @router.get(
        "/interviews/{interview_id}/transcript/download",
        response_class=FileResponse,
    )
    def download_transcript(
        interview_id: UUID,
        request: Request,
    ) -> FileResponse:
        record = _require_interview(interview_id, request)
        if record.artifact_root_path is None:
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

        filename = (
            f"{record.company}_{record.interview_datetime:%Y%m%d_%H%M}_"
            f"{record.recruiter_or_interviewer}_{record.sequence_number:02d}.txt"
        )
        safe_filename = "_".join(filename.split())

        return FileResponse(
            transcript_path,
            media_type="text/plain",
            filename=safe_filename,
        )

    return router
