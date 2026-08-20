# V1 Requirements

## 1. Functional Requirements

### FR-1 Audio Upload

The application must accept common interview recording formats including:

- WAV
- AAC
- M4A
- MP3

Additional FFmpeg-supported formats may be accepted where possible.

### FR-2 Audio Detection

The application must automatically detect:

- container
- codec
- duration
- sample rate
- channel count
- file size

Users should not need to manually convert files.

### FR-3 Audio Preprocessing

The system must determine whether audio can be consumed directly by the transcription engine.

Conversion should only occur when required.

FFmpeg/ffprobe should be preferred for audio inspection and normalization.

### FR-4 High-Quality Transcription

The system must support high-quality local transcription using Apple Silicon.

Initial reference engine:

MLX Whisper large-v3.

Alternative engines must implement a common transcription interface.

### FR-5 Speaker Diarization

The system must identify distinct speakers.

Users must be able to rename speakers, for example:

Speaker 1 → Interviewer

Speaker 2 → Candidate

### FR-6 Segment Timestamps

Every transcript segment must contain:

- start timestamp
- end timestamp
- speaker
- text

Segment timestamps are mandatory.

### FR-7 Silence Preservation

Silence may be skipped during inference where beneficial.

However, silence must remain represented in the original interview timeline.

Example:

[00:14:43 - 00:15:08] SILENCE - 25 seconds

### FR-8 Word-Level Timestamps

Word timestamps should be supported for:

- exact playback seeking
- transcript highlighting
- interactive audio navigation

Word timestamps must be architecturally separable from core segment timestamp generation where possible.

### FR-9 Real-Time Progress

The application must show real processing progress.

Stages should include:

- audio inspection
- audio preparation
- speech detection
- transcription
- diarization
- timestamp alignment
- export
- cloud synchronization

Progress should be derived from real processing metrics rather than fixed model-speed estimates wherever possible.

### FR-10 Interview Metadata

Each recording should support:

- company
- recruiter/interviewer name
- date
- time
- recording sequence
- role
- level
- interview round

Only company and recording metadata required for filename generation need to be mandatory initially.

### FR-11 Filename Convention

Artifacts from the same recording must share the same base filename.

Format:

timestamp_recruiter-name_sequence

Example:

2026-08-21_1615_ashok_01.aac

2026-08-21_1615_ashok_01.json

2026-08-21_1615_ashok_01.srt

2026-08-21_1615_ashok_01.md

Sequential calls use:

_01

_02

_03

### FR-12 Company Detection

The application may suggest the company using:

- user metadata
- filename
- transcript content
- company vocabulary

The user must be able to override the detected company.

### FR-13 Transcript Viewer

The local UI must support:

- transcript reading
- audio playback
- timestamp seeking
- speaker display
- search
- transcript editing
- speaker rename
- responsive layout

### FR-14 Transcript Export

Initial supported outputs:

- JSON
- Markdown
- SRT
- plain text

Additional formats may be added later.

### FR-15 Interview Library

Completed interviews must be searchable and browsable.

Initial dimensions:

- company
- date
- recruiter/interviewer
- interview round

### FR-16 Local Persistence

Local metadata and application state should use SQLite.

Audio and generated artifacts should be stored on the filesystem.

### FR-17 Cloud Synchronization

Users must be able to synchronize completed recordings and transcripts to cloud storage.

Initial target:

Cloudflare R2.

### FR-18 Always-Available Viewer

Cloud-synchronized interviews must remain accessible even when the local Mac is offline.

Initial hosting target:

Cloudflare Pages.

### FR-19 Sharing

The architecture must support shareable transcript URLs.

Future support should include:

- expiring links
- password protection
- revocation

### FR-20 Vocabulary Profiles

The transcription engine must support contextual vocabulary.

Initial built-in profile:

Staff / Engineering Manager software engineering interviews.

Example terminology:

Kafka

Redis

PostgreSQL

DynamoDB

idempotency

sharding

P99

SLA

SLO

CDC

Debezium

HLD

LLD

backpressure

operational excellence

Additional company/domain vocabulary may be layered on top.

## 2. Non-Functional Requirements

### NFR-1 Accuracy

Maximum practical transcription quality is the primary requirement.

Performance optimizations must not materially reduce transcript accuracy.

### NFR-2 Privacy

Interview recordings must remain local unless the user explicitly enables cloud synchronization.

### NFR-3 Apple Silicon Optimization

The local inference path should be optimized for:

- Apple M5
- 32 GB unified memory
- 10-core CPU
- 10-core GPU

### NFR-4 Performance Measurement

Each job should record metrics such as:

- audio duration
- preprocessing duration
- transcription duration
- diarization duration
- alignment duration
- export duration
- upload duration
- total duration
- real-time factor

### NFR-5 Reliability

Completed transcription state must survive application restarts.

Interrupted jobs should have clearly defined recovery behavior.

### NFR-6 Concurrency

The system must prevent uncontrolled simultaneous GPU-heavy transcription workloads.

Transcription should initially use an explicit worker queue.

### NFR-7 Maintainability

The system must follow a modular architecture.

Business logic must not remain concentrated inside UI/controller files.

### NFR-8 Extensibility

The following must use interfaces/adapters:

- transcription engines
- diarization engines
- storage providers
- AI evaluation providers
- exporters

### NFR-9 Testability

Core functionality must be covered by automated tests.

Tests should include:

- audio metadata
- filename generation
- transcript formatting
- segment handling
- silence handling
- persistence
- job lifecycle
- provider interfaces
- export generation

### NFR-10 Reproducibility

Python dependencies must be pinned using a lockfile.

Preferred environment:

uv + native Python environment.

### NFR-11 Observability

Application logs should be structured and associated with a job ID.

### NFR-12 Responsive UI

The transcript workspace must work correctly across common desktop viewport sizes without overlapping controls or inaccessible CTAs.

## 3. Future Requirements

These are intentionally outside initial implementation but must be supported architecturally.

### AI Interview Review

One-click interview evaluation using providers such as:

- OpenAI
- Anthropic Claude
- Google Gemini
- local models

### Structured AI Evaluation

Potential outputs:

- overall rating
- likely interview result
- expected hiring signal
- target-level assessment
- strengths
- weaknesses
- question-level feedback
- improved answers
- communication review
- technical review
- leadership review

### Section Detection

Automatically identify interview phases such as:

- introduction
- requirements
- HLD
- deep dive
- LLD
- coding
- leadership
- candidate questions

### Cross-Interview Analytics

Aggregate historical interview evaluations to identify:

- recurring weaknesses
- recurring strengths
- improvement trends
- performance by round
- performance by competency
- performance by target level

## 4. Explicit V1 Non-Goals

V1 will not initially require:

- microservices
- Kubernetes
- distributed transcription workers
- always-on cloud GPU infrastructure
- multi-user enterprise tenancy
- mobile applications
- billing
- subscriptions
- automated hiring decisions
