# ADR-002: Use a Modular Monolith

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

The prototype concentrates UI, orchestration, persistence, threading, transcription, and output logic into a small number of files.

V1 needs cleaner boundaries while remaining fast to develop and easy to run locally.

The system does not yet have the scale or organizational complexity that justifies microservices.

## Decision

V1 will use a modular monolith.

The backend will have explicit modules for:

- API
- domain models
- services
- audio processing
- transcription engines
- diarization
- repositories
- workers
- exporters
- cloud synchronization
- configuration
- observability

The UI will communicate with the local backend through a defined API boundary.

Business logic must not live inside UI components or API route handlers.

## Consequences

### Positive

- Simple local deployment.
- Fast AI-assisted development.
- Clear ownership and test boundaries.
- Easier future extraction of modules if needed.
- Avoids distributed-system complexity.

### Negative

- Module boundaries rely partly on engineering discipline.
- A single backend process still contains multiple capabilities.

## Alternatives Considered

### Keep the prototype structure

Rejected because it makes testing, extension, and production hardening increasingly difficult.

### Microservices

Rejected for V1 because they would introduce unnecessary deployment, networking, observability, and operational overhead.

## Follow-up

Architecture tests and code review conventions should prevent dependency leakage between modules.
