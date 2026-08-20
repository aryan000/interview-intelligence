from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from interview_intelligence.api.schemas import (
    InterviewCreateRequest,
    InterviewResponse,
    JobResponse,
    TranscriptResponse,
)
from interview_intelligence.persistence.models import InterviewRecord
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


def _interviews(request: Request) -> InterviewRepository:
    return cast(InterviewRepository, request.app.state.interviews)


def _jobs(request: Request) -> ProcessingJobRepository:
    return cast(ProcessingJobRepository, request.app.state.jobs)


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
        _interviews(request).save(record)
        return _to_interview_response(record)

    @router.get(
        "/interviews/{interview_id}",
        response_model=InterviewResponse,
    )
    def get_interview(
        interview_id: UUID,
        request: Request,
    ) -> InterviewResponse:
        record = _interviews(request).get(interview_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )
        return _to_interview_response(record)

    @router.get(
        "/jobs/{job_id}",
        response_model=JobResponse,
    )
    def get_job(job_id: UUID, request: Request) -> JobResponse:
        job = _jobs(request).get(job_id)
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

    @router.get(
        "/interviews/{interview_id}/transcript",
        response_model=TranscriptResponse,
    )
    def get_transcript(
        interview_id: UUID,
        request: Request,
    ) -> TranscriptResponse:
        record = _interviews(request).get(interview_id)
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
        record = _interviews(request).get(interview_id)
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
