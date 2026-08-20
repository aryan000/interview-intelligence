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
