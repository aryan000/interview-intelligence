from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class HiringSignal(StrEnum):
    STRONG_NO_HIRE = "strong_no_hire"
    NO_HIRE = "no_hire"
    MIXED = "mixed"
    HIRE = "hire"
    STRONG_HIRE = "strong_hire"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewRequest(BaseModel):
    interview_id: str
    company: str
    role: str | None = None
    target_level: str | None = None
    round_type: str | None = None
    transcript_path: Path


class QuestionReview(BaseModel):
    sequence_number: int = Field(ge=1)
    question: str
    question_start_seconds: float | None = Field(default=None, ge=0)
    answer_summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    stronger_answer: str | None = None
    rating: float | None = Field(default=None, ge=1, le=5)
    level_signal: str | None = None


class ReviewUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    pricing_basis: str | None = None


class ReviewAnalysisMetadata(BaseModel):
    started_at: datetime
    completed_at: datetime
    elapsed_seconds: float = Field(ge=0)


class InterviewReview(BaseModel):
    interview_id: str
    provider: str
    model: str

    overall_summary: str
    hiring_signal: HiringSignal
    confidence: float = Field(ge=0, le=1)

    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    questions: list[QuestionReview] = Field(default_factory=list)

    role_signal: str | None = None
    level_signal: str | None = None

    usage: ReviewUsage | None = None
    analysis: ReviewAnalysisMetadata | None = None
