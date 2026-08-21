from pathlib import Path

from interview_intelligence.review.engines.openai_engine import OpenAIReviewEngine
from interview_intelligence.review.models import HiringSignal, ReviewRequest


class StubInputDetails:
    cached_tokens = 1_000
    cache_write_tokens = 500


class StubOutputDetails:
    reasoning_tokens = 300


class StubUsage:
    input_tokens = 10_000
    input_tokens_details = StubInputDetails()
    output_tokens = 2_000
    output_tokens_details = StubOutputDetails()
    total_tokens = 12_000


class StubModelReview:
    overall_summary = "Good technical depth."
    hiring_signal = HiringSignal.HIRE
    confidence = 0.8
    strengths = ["Good evidence"]
    concerns: list[str] = []
    improvement_areas: list[str] = []
    questions: list[object] = []
    role_signal = "EM evidence"
    level_signal = "Meets bar"


class StubParsedResponse:
    def __init__(self) -> None:
        self.output_parsed = StubModelReview()
        self.usage = StubUsage()


class StubResponses:
    def __init__(self) -> None:
        self.model: str | None = None
        self.input: str | None = None
        self.text_format: type[object] | None = None

    def parse(
        self,
        *,
        model: str,
        input: str,
        text_format: type[object],
    ) -> StubParsedResponse:
        self.model = model
        self.input = input
        self.text_format = text_format
        return StubParsedResponse()


class StubOpenAI:
    def __init__(self) -> None:
        self.responses = StubResponses()


def test_openai_engine_captures_usage_and_cost() -> None:
    client = StubOpenAI()
    engine = OpenAIReviewEngine(
        model="gpt-5.6-sol",
        client=client,  # type: ignore[arg-type]
    )

    result = engine.review(
        ReviewRequest(
            interview_id="abc",
            company="PhonePe",
            role="Engineering Manager",
            round_type="HLD",
            transcript_path=Path("/tmp/transcript.txt"),
        ),
        "[00:00:00 -> 00:00:05] Interviewer: Tell me about yourself.",
    )

    assert result.interview_id == "abc"
    assert result.provider == "openai"
    assert result.model == "gpt-5.6-sol"
    assert result.hiring_signal == HiringSignal.HIRE
    assert result.usage is not None
    assert result.usage.input_tokens == 10_000
    assert result.usage.cached_input_tokens == 1_000
    assert result.usage.cache_write_tokens == 500
    assert result.usage.output_tokens == 2_000
    assert result.usage.reasoning_tokens == 300
    assert result.usage.total_tokens == 12_000
    assert result.usage.estimated_cost_usd is not None
    assert result.usage.estimated_cost_usd > 0
    assert client.responses.model == "gpt-5.6-sol"
    assert "PhonePe" in (client.responses.input or "")
    assert "HLD" in (client.responses.input or "")
