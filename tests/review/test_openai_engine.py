from pathlib import Path

from interview_intelligence.review.engines.openai_engine import OpenAIReviewEngine
from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    ReviewRequest,
)


class StubParsedResponse:
    def __init__(self, review: InterviewReview) -> None:
        self.output_parsed = review


class StubResponses:
    def __init__(self, review: InterviewReview) -> None:
        self.review = review
        self.model: str | None = None
        self.input: str | None = None
        self.text_format: type[InterviewReview] | None = None

    def parse(
        self,
        *,
        model: str,
        input: str,
        text_format: type[InterviewReview],
    ) -> StubParsedResponse:
        self.model = model
        self.input = input
        self.text_format = text_format
        return StubParsedResponse(self.review)


class StubOpenAI:
    def __init__(self, review: InterviewReview) -> None:
        self.responses = StubResponses(review)


def test_openai_engine_returns_structured_review() -> None:
    model_review = InterviewReview(
        interview_id="model-generated",
        provider="model-generated",
        model="model-generated",
        overall_summary="Good technical depth.",
        hiring_signal=HiringSignal.HIRE,
        confidence=0.8,
    )
    client = StubOpenAI(model_review)

    engine = OpenAIReviewEngine(
        model="gpt-test",
        client=client,  # type: ignore[arg-type]
    )

    result = engine.review(
        ReviewRequest(
            interview_id="abc",
            company="PhonePe",
            role="Engineering Manager",
            transcript_path=Path("/tmp/transcript.txt"),
        ),
        "[00:00:00 -> 00:00:05] Interviewer: Tell me about yourself.",
    )

    assert result.interview_id == "abc"
    assert result.provider == "openai"
    assert result.model == "gpt-test"
    assert client.responses.model == "gpt-test"
    assert client.responses.text_format is InterviewReview
    assert "PhonePe" in (client.responses.input or "")
