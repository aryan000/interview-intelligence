from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from interview_intelligence.domain.enums import JobStage, JobStatus


class JobProgressEvent(BaseModel):
    job_id: UUID
    interview_id: UUID
    status: JobStatus
    stage: JobStage
    progress_percent: float = Field(ge=0, le=100)
    processed_audio_seconds: float = Field(ge=0)
    total_audio_seconds: float = Field(ge=0)
    message: str | None = None
    occurred_at: datetime
