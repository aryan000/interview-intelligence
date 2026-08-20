from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Interview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company: str
    role: str | None = None
    target_level: str | None = None
    round_type: str | None = None
    interviewer_name: str | None = None
    interview_date: datetime

    @field_validator("company")
    @classmethod
    def company_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("company must not be blank")
        return cleaned


class Recording(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    interview_id: UUID
    sequence_number: int = Field(ge=1)
    source_filename: str
    source_path: Path
    canonical_basename: str
    duration_seconds: float | None = Field(default=None, ge=0)
    format: str | None = None
    codec: str | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)
    file_size_bytes: int | None = Field(default=None, ge=0)


class TranscriptSegment(BaseModel):
    sequence_number: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker_id: str | None = None
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "TranscriptSegment":
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        return self


class SilenceInterval(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "SilenceInterval":
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        return self

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds
