# Architecture

## Overview

Interview Intelligence is a local-first modular monolith with a separate cloud viewer.

The local Mac application performs transcription, diarization, timestamp processing, persistence, and synchronization.

The cloud application stores completed artifacts and provides an always-available interview library and transcript viewer.

## High-Level Architecture

```text
                         LOCAL MAC

┌────────────────────────────────────────────────────────────┐
│                         Local UI                           │
│                  React / Web Frontend                      │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│                        FastAPI                             │
│                                                          │
│  Jobs API   Transcript API   Library API   Settings API   │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│                     Service Layer                          │
│                                                          │
│  JobService                                              │
│  TranscriptionService                                    │
│  InterviewService                                        │
│  ExportService                                           │
│  CloudSyncService                                        │
└───────────────────────┬────────────────────────────────────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
 Transcription       Diarization      Audio Pipeline
    Engine              Engine
        │               │                │
        └───────────────┼────────────────┘
                        │
                        ▼
                 Worker / Job Queue
                        │
                ┌───────┴────────┐
                ▼                ▼
              SQLite          Filesystem


                         CLOUD

┌────────────────────────────────────────────────────────────┐
│                  Cloudflare Pages                          │
│             Interview Library / Viewer                     │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                    Cloudflare R2                           │
│                                                          │
│ Audio | Transcript JSON | SRT | Markdown | Metadata       │
└────────────────────────────────────────────────────────────┘
```

## Architectural Style

The application uses a modular monolith.

This means:

- one deployable local backend
- clear internal module boundaries
- interfaces between major capabilities
- no microservices in V1

This keeps local development and deployment simple while allowing future extraction of components if needed.

## Main Modules

### API Layer

Responsibilities:

- HTTP endpoints
- request validation
- response formatting
- authentication hooks if needed later

The API layer must not contain transcription business logic.

### Domain Layer

Contains core models such as:

- Interview
- Recording
- Transcript
- TranscriptSegment
- Speaker
- SilenceInterval
- Job
- JobStage

Domain objects should be independent of FastAPI, SQLite, MLX, Cloudflare, or AI providers.

### Service Layer

Coordinates business workflows.

Examples:

- create interview
- create transcription job
- start transcription
- update metadata
- rename speaker
- export transcript
- synchronize job to cloud

### Audio Module

Responsible for:

- ffprobe metadata detection
- codec detection
- format support checks
- conversion when required
- resampling
- channel normalization
- speech/silence detection

### Transcription Engine

Defined behind an interface.

Initial implementation:

MLXWhisperEngine

Future implementations may include:

- FasterWhisperEngine
- WhisperCppEngine
- CloudTranscriptionEngine

### Diarization Engine

Defined behind an interface.

Responsibilities:

- identify speaker turns
- assign speaker IDs
- align speaker turns with transcript segments

### Persistence Layer

SQLite stores structured application state.

Filesystem stores:

- source recordings
- intermediate files
- transcript artifacts
- exports

Repositories hide persistence details from services.

### Worker Layer

GPU-heavy transcription must run through an explicit worker queue.

Initial policy:

- one active GPU transcription at a time
- CPU-based preprocessing may run concurrently where safe

This avoids uncontrolled GPU contention.

### Export Layer

Exporters generate:

- JSON
- Markdown
- SRT
- TXT

Future formats can be added without modifying transcription logic.

### Cloud Sync Layer

Responsible for:

- upload to Cloudflare R2
- artifact synchronization
- cloud object naming
- retry handling
- synchronization state

Cloud sync is optional.

Local transcription must continue to work without internet access.

## Pluggable Interfaces

The following capabilities must use adapters/interfaces:

### TranscriptionEngine

```python
class TranscriptionEngine:
    def transcribe(self, request):
        ...
```

### DiarizationEngine

```python
class DiarizationEngine:
    def diarize(self, audio):
        ...
```

### StorageProvider

```python
class StorageProvider:
    def upload(self, artifact):
        ...
```

### AIReviewProvider

Future interface:

```python
class AIReviewProvider:
    def review(self, interview, transcript, context):
        ...
```

Implementations may include:

- OpenAI
- Gemini
- Claude
- local models

## Local Data Directory

Application data should live outside the Git repository.

Suggested macOS location:

```text
~/Library/Application Support/InterviewIntelligence/
```

Example:

```text
InterviewIntelligence/
├── app.db
├── recordings/
├── jobs/
├── exports/
├── cache/
└── logs/
```

## Repository Layout

```text
src/interview_intelligence/
├── api/
├── domain/
├── services/
├── audio/
├── engines/
├── diarization/
├── repositories/
├── workers/
├── exporters/
├── cloud/
├── config/
└── observability/
```

## Design Principles

1. UI must not own business logic.
2. API must not own transcription logic.
3. MLX must remain isolated behind an engine interface.
4. SQLite access must remain behind repositories.
5. Cloudflare-specific logic must remain behind cloud adapters.
6. AI provider-specific logic must remain behind AI provider adapters.
7. Local transcription must work fully offline.
8. Cloud synchronization must be optional.
9. Quality is more important than processing speed.
10. Measure performance before optimizing.
