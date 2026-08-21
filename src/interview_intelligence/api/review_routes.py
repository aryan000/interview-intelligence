import json
import os
from pathlib import Path
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from interview_intelligence.persistence.repositories import InterviewRepository
from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.engines.openai_engine import OpenAIReviewEngine
from interview_intelligence.review.models import InterviewReview, ReviewRequest
from interview_intelligence.review.pricing import MODEL_RATES, PRICING_BASIS
from interview_intelligence.review.service import InterviewReviewService


class ReviewConfigResponse(BaseModel):
    provider: str
    model: str
    pricing_basis: str | None = None
    input_per_million_usd: float | None = None
    cached_input_per_million_usd: float | None = None
    cache_write_per_million_usd: float | None = None
    output_per_million_usd: float | None = None


class ReviewCreateRequest(BaseModel):
    model: str | None = None


_ALLOWED_REVIEW_MODELS = {
    "gpt-5.6-luna",
    "gpt-5.6-sol",
}
_DEFAULT_REVIEW_MODEL = "gpt-5.6-luna"


def _interviews(request: Request) -> InterviewRepository:
    return cast(InterviewRepository, request.app.state.interviews)


def _configured_model(request: Request) -> str:
    configured = getattr(request.app.state, "review_engine", None)
    if configured is not None:
        return str(getattr(configured, "model", "configured-provider"))

    return os.getenv(
        "INTERVIEW_INTELLIGENCE_REVIEW_MODEL",
        _DEFAULT_REVIEW_MODEL,
    )


def _review_engine(
    request: Request,
    model_override: str | None = None,
) -> InterviewReviewEngine:
    configured = getattr(request.app.state, "review_engine", None)
    if configured is not None:
        return cast(InterviewReviewEngine, configured)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )

    model = model_override or _configured_model(request)
    if model not in _ALLOWED_REVIEW_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported review model. Choose gpt-5.6-luna or gpt-5.6-sol.",
        )

    return OpenAIReviewEngine(model=model)


def build_review_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/review/config", response_model=ReviewConfigResponse)
    def get_review_config(request: Request) -> ReviewConfigResponse:
        model = _configured_model(request)
        rates = MODEL_RATES.get(model)

        return ReviewConfigResponse(
            provider="openai",
            model=model,
            pricing_basis=PRICING_BASIS if rates is not None else None,
            input_per_million_usd=(
                rates.input_per_million if rates is not None else None
            ),
            cached_input_per_million_usd=(
                rates.cached_input_per_million if rates is not None else None
            ),
            cache_write_per_million_usd=(
                rates.cache_write_per_million if rates is not None else None
            ),
            output_per_million_usd=(
                rates.output_per_million if rates is not None else None
            ),
        )

    @router.post(
        "/interviews/{interview_id}/review",
        response_model=InterviewReview,
    )
    def create_review(
        interview_id: UUID,
        request: Request,
        payload: ReviewCreateRequest | None = None,
    ) -> InterviewReview:
        interview = _interviews(request).get(interview_id)
        if interview is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        if interview.artifact_root_path is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interview has not been processed",
            )

        artifact_root = Path(interview.artifact_root_path)
        transcript_path = artifact_root / "transcript.txt"
        review_path = artifact_root / "review.json"

        review_request = ReviewRequest(
            interview_id=str(interview.id),
            company=interview.company,
            role=interview.role,
            target_level=interview.target_level,
            round_type=interview.round_type,
            transcript_path=transcript_path,
        )

        try:
            selected_model = payload.model if payload is not None else None
            return InterviewReviewService(
                _review_engine(request, selected_model)
            ).run(
                review_request,
                review_path,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    @router.get(
        "/interviews/{interview_id}/review",
        response_model=InterviewReview,
    )
    def get_review(
        interview_id: UUID,
        request: Request,
    ) -> InterviewReview:
        interview = _interviews(request).get(interview_id)
        if interview is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        if interview.artifact_root_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )

        review_path = Path(interview.artifact_root_path) / "review.json"
        if not review_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )

        return InterviewReview.model_validate(
            json.loads(review_path.read_text(encoding="utf-8"))
        )

    return router
