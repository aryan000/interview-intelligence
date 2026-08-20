# ADR-006: Keep AI Interview Review Provider-Agnostic

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Today, transcript review is performed manually by uploading transcripts to an AI assistant and supplying role, level, company, and round context.

The future product should reduce this to a one-click interview review.

Model quality, pricing, capabilities, and availability change over time. The product should not be tightly coupled to a single AI provider.

## Decision

Introduce AI review through a provider-neutral `AIReviewProvider` interface.

Potential adapters include:

- OpenAI
- Google Gemini
- Anthropic Claude
- local models
- future providers

AI review is not required for the initial transcription engine release, but the domain model and architecture must leave a clean extension point for it.

A review request should contain structured context such as:

- transcript
- timeline
- speakers
- company
- role
- target level
- round type
- optional evaluation rubric

Providers should return a normalized structured result rather than provider-specific free-form data.

## Expected Future Output

The normalized review may contain:

- overall rating
- likely outcome
- target-level assessment
- competency scores
- strengths
- growth areas
- question-by-question feedback
- evidence linked to transcript timestamps
- suggested improved answers
- recommended practice areas

## Consequences

### Positive

- Providers can be compared or changed.
- Avoids vendor lock-in.
- Enables future local-model support.
- The UI can consume one normalized review model.
- Makes one-click review possible.

### Negative

- Provider capabilities do not map perfectly to one schema.
- Adapter maintenance is required.
- Prompt/evaluation consistency must be managed across models.

## Alternatives Considered

### Hard-code one provider

Rejected because model providers evolve quickly and users may prefer different models for privacy, cost, or quality.

### Keep manual copy/paste review forever

Rejected because it breaks the desired end-to-end feedback loop.

## Follow-up

Before implementing AI review, define a versioned evaluation rubric and structured response schema so scores remain comparable across interviews and model versions.
