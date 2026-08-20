from typing import Protocol, cast

from openai import OpenAI

from interview_intelligence.review.engines.base import InterviewReviewEngine
from interview_intelligence.review.models import InterviewReview, ReviewRequest
from interview_intelligence.review.prompts import build_review_prompt


class _ParsedResponse(Protocol):
    output_parsed: InterviewReview | None


class _ResponsesClient(Protocol):
    def parse(
        self,
        *,
        model: str,
        input: str,
        text_format: type[InterviewReview],
    ) -> _ParsedResponse: ...


class OpenAIReviewEngine(InterviewReviewEngine):
    """OpenAI-backed structured interview reviewer."""

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
            text_format=InterviewReview,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no structured interview review")

        # Provider/model are controlled by the engine, not trusted to model output.
        return parsed.model_copy(
            update={
                "interview_id": request.interview_id,
                "provider": "openai",
                "model": self.model,
            }
        )
