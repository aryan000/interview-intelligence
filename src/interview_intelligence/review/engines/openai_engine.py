from typing import Protocol, cast

from openai import OpenAI
from pydantic import BaseModel, Field

from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    QuestionReview,
    ReviewRequest,
    ReviewUsage,
)
from interview_intelligence.review.pricing import estimate_cost_usd
from interview_intelligence.review.prompts import build_review_prompt


class _ModelInterviewReview(BaseModel):
    overall_summary: str
    hiring_signal: HiringSignal
    confidence: float = Field(ge=0, le=1)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    questions: list[QuestionReview] = Field(default_factory=list)
    role_signal: str | None = None
    level_signal: str | None = None


class _InputTokenDetails(Protocol):
    cached_tokens: int
    cache_write_tokens: int


class _OutputTokenDetails(Protocol):
    reasoning_tokens: int


class _Usage(Protocol):
    input_tokens: int
    input_tokens_details: _InputTokenDetails
    output_tokens: int
    output_tokens_details: _OutputTokenDetails
    total_tokens: int


class _ParsedResponse(Protocol):
    output_parsed: _ModelInterviewReview | None
    usage: _Usage | None


class _ResponsesClient(Protocol):
    def parse(
        self,
        *,
        model: str,
        input: str,
        text_format: type[_ModelInterviewReview],
    ) -> _ParsedResponse: ...


class OpenAIReviewEngine(InterviewReviewEngine):
    """OpenAI-backed structured interview reviewer with usage capture."""

    def __init__(
        self,
        model: str = "gpt-5.6-sol",
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.client = client or OpenAI()

    def review(
        self,
        request: ReviewRequest,
        transcript: str,
    ) -> InterviewReview:
        responses = cast(_ResponsesClient, self.client.responses)
        response = responses.parse(
            model=self.model,
            input=build_review_prompt(request, transcript),
            text_format=_ModelInterviewReview,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no structured interview review")

        usage = self._usage(response.usage)
        estimated_cost_usd, pricing_basis = estimate_cost_usd(
            self.model,
            usage,
        )
        usage = usage.model_copy(
            update={
                "estimated_cost_usd": estimated_cost_usd,
                "pricing_basis": pricing_basis,
            }
        )

        return InterviewReview(
            interview_id=request.interview_id,
            provider="openai",
            model=self.model,
            overall_summary=parsed.overall_summary,
            hiring_signal=parsed.hiring_signal,
            confidence=parsed.confidence,
            strengths=parsed.strengths,
            concerns=parsed.concerns,
            improvement_areas=parsed.improvement_areas,
            questions=parsed.questions,
            role_signal=parsed.role_signal,
            level_signal=parsed.level_signal,
            usage=usage,
        )

    @staticmethod
    def _usage(raw: _Usage | None) -> ReviewUsage:
        if raw is None:
            return ReviewUsage()

        input_details = getattr(raw, "input_tokens_details", None)
        output_details = getattr(raw, "output_tokens_details", None)

        return ReviewUsage(
            input_tokens=getattr(raw, "input_tokens", 0) or 0,
            cached_input_tokens=(
                getattr(input_details, "cached_tokens", 0) or 0
            ),
            cache_write_tokens=(
                getattr(input_details, "cache_write_tokens", 0) or 0
            ),
            output_tokens=getattr(raw, "output_tokens", 0) or 0,
            reasoning_tokens=(
                getattr(output_details, "reasoning_tokens", 0) or 0
            ),
            total_tokens=getattr(raw, "total_tokens", 0) or 0,
        )
