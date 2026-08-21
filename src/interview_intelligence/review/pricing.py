from dataclasses import dataclass

from interview_intelligence.review.models import ReviewUsage


@dataclass(frozen=True)
class TokenRates:
    input_per_million: float
    cached_input_per_million: float
    cache_write_per_million: float | None
    output_per_million: float
    long_context_input_per_million: float | None = None
    long_context_cached_input_per_million: float | None = None
    long_context_cache_write_per_million: float | None = None
    long_context_output_per_million: float | None = None
    long_context_threshold: int | None = None


PRICING_BASIS = "OpenAI standard API pricing checked 2026-08-21"

MODEL_RATES: dict[str, TokenRates] = {
    "gpt-5.6-sol": TokenRates(
        input_per_million=5.00,
        cached_input_per_million=0.50,
        cache_write_per_million=6.25,
        output_per_million=30.00,
        long_context_input_per_million=10.00,
        long_context_cached_input_per_million=1.00,
        long_context_cache_write_per_million=12.50,
        long_context_output_per_million=45.00,
        long_context_threshold=272_000,
    ),
    "gpt-5.6": TokenRates(
        input_per_million=5.00,
        cached_input_per_million=0.50,
        cache_write_per_million=6.25,
        output_per_million=30.00,
        long_context_input_per_million=10.00,
        long_context_cached_input_per_million=1.00,
        long_context_cache_write_per_million=12.50,
        long_context_output_per_million=45.00,
        long_context_threshold=272_000,
    ),
    "gpt-5.6-terra": TokenRates(
        input_per_million=2.50,
        cached_input_per_million=0.25,
        cache_write_per_million=3.125,
        output_per_million=15.00,
        long_context_input_per_million=5.00,
        long_context_cached_input_per_million=0.50,
        long_context_cache_write_per_million=6.25,
        long_context_output_per_million=22.50,
        long_context_threshold=272_000,
    ),
    "gpt-5.6-luna": TokenRates(
        input_per_million=1.00,
        cached_input_per_million=0.10,
        cache_write_per_million=1.25,
        output_per_million=6.00,
        long_context_input_per_million=2.00,
        long_context_cached_input_per_million=0.20,
        long_context_cache_write_per_million=2.50,
        long_context_output_per_million=9.00,
        long_context_threshold=272_000,
    ),
    "gpt-5.4": TokenRates(
        input_per_million=2.50,
        cached_input_per_million=0.25,
        cache_write_per_million=None,
        output_per_million=15.00,
        long_context_input_per_million=5.00,
        long_context_cached_input_per_million=0.50,
        long_context_output_per_million=22.50,
        long_context_threshold=272_000,
    ),
}


def estimate_cost_usd(model: str, usage: ReviewUsage) -> tuple[float | None, str | None]:
    rates = MODEL_RATES.get(model)
    if rates is None:
        return None, None

    long_context = (
        rates.long_context_threshold is not None
        and usage.input_tokens > rates.long_context_threshold
    )

    if long_context:
        input_rate = rates.long_context_input_per_million or rates.input_per_million
        cached_rate = (
            rates.long_context_cached_input_per_million
            or rates.cached_input_per_million
        )
        cache_write_rate = (
            rates.long_context_cache_write_per_million
            if rates.long_context_cache_write_per_million is not None
            else rates.cache_write_per_million
        )
        output_rate = (
            rates.long_context_output_per_million
            or rates.output_per_million
        )
    else:
        input_rate = rates.input_per_million
        cached_rate = rates.cached_input_per_million
        cache_write_rate = rates.cache_write_per_million
        output_rate = rates.output_per_million

    cached = min(usage.cached_input_tokens, usage.input_tokens)
    cache_write = min(
        usage.cache_write_tokens,
        max(0, usage.input_tokens - cached),
    )
    uncached = max(0, usage.input_tokens - cached - cache_write)

    cost = (
        uncached * input_rate
        + cached * cached_rate
        + usage.output_tokens * output_rate
    ) / 1_000_000

    if cache_write_rate is not None:
        cost += cache_write * cache_write_rate / 1_000_000
    else:
        cost += cache_write * input_rate / 1_000_000

    context_note = " · long-context rates" if long_context else ""
    return round(cost, 6), f"{PRICING_BASIS}{context_note}"
