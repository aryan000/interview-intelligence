from dataclasses import dataclass


@dataclass(frozen=True)
class VocabularyProfile:
    name: str
    prompt: str


STAFF_EM_SOFTWARE_ENGINEERING = VocabularyProfile(
    name="staff-em-software-engineering",
    prompt=(
        "This is a senior software engineering interview for Staff Engineer or "
        "Engineering Manager roles. Technical vocabulary may include: "
        "distributed systems, system design, HLD, LLD, Kafka, Redis, PostgreSQL, "
        "DynamoDB, SQS, SNS, CDC, Debezium, idempotency, consistency, replication, "
        "sharding, partitioning, leader election, backpressure, caching, P99 latency, "
        "SLA, SLO, availability, scalability, throughput, operational excellence, "
        "stakeholder management, prioritization, trade-offs, observability, metrics, "
        "alerts, deployment, rollback, microservices, APIs, database indexing, "
        "optimistic locking, transactions, and failure handling."
    ),
)


def build_interview_prompt(
    company: str | None = None,
    extra_terms: list[str] | None = None,
) -> str:
    parts = [STAFF_EM_SOFTWARE_ENGINEERING.prompt]

    if company:
        parts.append(f"The company being discussed is {company.strip()}.")

    if extra_terms:
        cleaned = [term.strip() for term in extra_terms if term.strip()]
        if cleaned:
            parts.append("Additional expected terms: " + ", ".join(cleaned) + ".")

    return " ".join(parts)
