import json
import os
from pathlib import Path
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from interview_intelligence.persistence.repositories import InterviewRepository
from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.engines.openai_engine import OpenAIReviewEngine
from interview_intelligence.review.models import InterviewReview, ReviewRequest
from interview_intelligence.review.service import InterviewReviewService


def _interviews(request: Request) -> InterviewRepository:
    return cast(InterviewRepository, request.app.state.interviews)


def _review_engine(request: Request) -> InterviewReviewEngine:
    configured = getattr(request.app.state, "review_engine", None)
    if configured is not None:
        return cast(InterviewReviewEngine, configured)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured",
        )

    model = os.getenv(
        "INTERVIEW_INTELLIGENCE_REVIEW_MODEL",
        "gpt-5.6-sol",
    )
    return OpenAIReviewEngine(model=model)


def build_review_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.post(
        "/interviews/{interview_id}/review",
        response_model=InterviewReview,
    )
    def create_review(
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
            transcript_path=transcript_path,
        )

        try:
            return InterviewReviewService(_review_engine(request)).run(
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
