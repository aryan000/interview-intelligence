# ADR-003: Use SQLite for Local Structured Storage

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

The prototype persists job state using JSON files.

V1 requires durable and queryable state for interviews, recordings, jobs, transcripts, speakers, silence intervals, artifacts, metrics, and future AI reviews.

The primary application is single-machine and local-first.

## Decision

Use SQLite for structured local application state.

Store large binary artifacts such as audio recordings and generated files on the filesystem rather than as SQLite BLOBs.

The database should live under the application's macOS data directory, for example:

`~/Library/Application Support/InterviewIntelligence/app.db`

SQLite access must be isolated behind repository interfaces.

## Consequences

### Positive

- No separate database server.
- Transactional writes.
- Easy backup and portability.
- Strong fit for a local desktop/server application.
- Supports richer queries than JSON-file persistence.
- Straightforward testing.

### Negative

- Not intended to become the shared database for a multi-user cloud service.
- Concurrent write patterns must remain controlled.

## Alternatives Considered

### JSON files

Rejected because they provide weak transactional behavior, awkward querying, and poor schema evolution.

### Local PostgreSQL

Rejected for V1 because it adds unnecessary installation and operational overhead.

### PostgreSQL in Docker

Rejected for the local application because SQLite satisfies current requirements with much less complexity.

## Follow-up

If a future hosted multi-user product requires shared transactional state, introduce a cloud database behind the same repository/service boundaries.
