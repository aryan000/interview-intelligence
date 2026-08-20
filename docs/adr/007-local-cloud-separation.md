# ADR-007: Separate Local Transcription from the Cloud Workspace

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Transcription is compute-heavy and benefits from the user's Apple Silicon hardware.

The interview library and transcript viewer are lightweight but must remain accessible when the Mac is turned off.

Combining these responsibilities would either require the Mac to remain online or require moving transcription into paid cloud compute.

## Decision

Treat the system as two cooperating applications.

### Local Application

Responsible for:

- audio ingestion
- audio inspection and preprocessing
- transcription
- diarization
- timeline alignment
- real-time processing progress
- local transcript review/editing
- SQLite persistence
- artifact generation
- optional cloud synchronization

### Cloud Workspace

Responsible for:

- always-available interview library
- company/date organization
- transcript viewing
- audio playback
- searching
- synchronized metadata
- controlled sharing
- future display of AI review results

The cloud workspace must not require the local Mac to be online after synchronization completes.

## Synchronization Boundary

Completed artifacts are the boundary between local compute and cloud access.

The local application uploads immutable or versioned artifacts and metadata through a storage/synchronization adapter.

A cloud failure must not cause local transcription to fail.

## Consequences

### Positive

- Local ML performance and privacy are preserved.
- Cloud hosting remains lightweight.
- The Mac can be turned off.
- Local and cloud UIs can evolve independently.
- Future cloud transcription can be added as another engine rather than redesigning the product.

### Negative

- Requires synchronization state and retry behavior.
- Local edits after synchronization require a resync/versioning strategy.
- There are two UI deployment targets.

## Alternatives Considered

### One local Gradio application exposed publicly

Rejected because availability depends on the Mac.

### Fully hosted application

Rejected for V1 because cloud inference adds cost and reduces the local-first privacy advantage.

## Follow-up

Define synchronization semantics for transcript edits, deletions, artifact versioning, and conflict handling before cloud editing is introduced.
