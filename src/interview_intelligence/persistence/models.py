from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from interview_intelligence.domain.enums import JobStage, JobStatus


class InterviewRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company: str
    recruiter_or_interviewer: str
    interview_datetime: datetime
    sequence_number: int = Field(ge=1)
    role: str | None = None
    target_level: str | None = None
    round_type: str | None = None
    source_audio_path: str
    artifact_root_path: str | None = None
    transcription_seconds: float | None = Field(default=None, ge=0)
    diarization_seconds: float | None = Field(default=None, ge=0)
    total_processing_seconds: float | None = Field(default=None, ge=0)
    created_at: datetime
    updated_at: datetime


class ProcessingJobRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    interview_id: UUID
    status: JobStatus
    stage: JobStage
    progress_percent: float = Field(ge=0, le=100)
    processed_audio_seconds: float = Field(ge=0)
    total_audio_seconds: float = Field(ge=0)
    message: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
