from interview_intelligence.engines.vocabulary import build_interview_prompt


def test_prompt_contains_staff_em_context() -> None:
    prompt = build_interview_prompt()

    assert "Staff Engineer" in prompt
    assert "Engineering Manager" in prompt
    assert "Kafka" in prompt
    assert "idempotency" in prompt


def test_prompt_can_include_company_and_extra_terms() -> None:
    prompt = build_interview_prompt(
        company="PhonePe",
        extra_terms=["UPI", "payment gateway"],
    )

    assert "PhonePe" in prompt
    assert "UPI" in prompt
    assert "payment gateway" in prompt
