from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from interview_intelligence.domain.enums import JobStage, JobStatus


class InterviewCreateRequest(BaseModel):
    company: str = Field(min_length=1)
    recruiter_or_interviewer: str = Field(min_length=1)
    interview_datetime: datetime
    sequence_number: int = Field(default=1, ge=1)
    role: str | None = None
    target_level: str | None = None
    source_audio_path: str = Field(min_length=1)


class InterviewResponse(BaseModel):
    id: UUID
    company: str
    recruiter_or_interviewer: str
    interview_datetime: datetime
    sequence_number: int
    role: str | None
    target_level: str | None
    source_audio_path: str
    artifact_root_path: str | None
    duration_seconds: float | None = None


class JobResponse(BaseModel):
    id: UUID
    interview_id: UUID
    status: JobStatus
    stage: JobStage
    progress_percent: float
    processed_audio_seconds: float
    total_audio_seconds: float
    message: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProcessInterviewResponse(BaseModel):
    job_id: UUID
    interview_id: UUID
    status: JobStatus


class TranscriptResponse(BaseModel):
    interview_id: UUID
    transcript: str
