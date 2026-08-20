# Interview IntelliSense — V1 Technical Specification

**Status:** Draft v1.0  
**Product type:** Local-first interview transcription + cloud interview workspace  
**Primary constraint:** Maximum transcription quality is non-negotiable. Speed optimizations are accepted only when they do not materially reduce transcription or diarization quality.

---

## 1. Product Vision

Interview IntelliSense turns every interview into a structured feedback loop.

The first layer captures and transcribes interview recordings locally with high accuracy, speaker separation, timestamps, silence preservation, and searchable outputs. The second layer synchronizes completed artifacts to a lightweight always-online cloud workspace for browsing, playback, sharing, and later AI-assisted evaluation.

The long-term product is not a generic transcription utility. It is an interview intelligence system that helps users:

- understand how each interview round went,
- identify recurring strengths and weaknesses,
- understand where time was spent,
- compare performance across companies and rounds,
- estimate likely role/level outcome,
- receive actionable improvement guidance,
- reduce the manual process of uploading transcripts into separate AI chats.

---

## 2. Core Product Principles

1. **Quality first**  
   Large-v3 is the reference transcription model until another model is proven equivalent on the user's interview corpus.

2. **Local-first processing**  
   Raw transcription and diarization run locally on Apple Silicon by default.

3. **Cloud only where useful**  
   Cloud is used for durable transcript/audio access, sharing, browsing, and future AI analysis orchestration.

4. **Privacy-aware by design**  
   Cloud sync is explicit. Raw recordings are not automatically published publicly.

5. **Pluggable engines**  
   Transcription, diarization, storage, and AI evaluation providers must be replaceable behind interfaces.

6. **Modular monolith first**  
   No premature microservices.

7. **Repository as source of truth**  
   Product decisions, architecture, requirements, benchmarks, and ADRs must live in the repository.

---

## 3. V1 Scope

V1 consists of two user-facing experiences.

### 3.1 Local Transcript Studio

Runs on the user's Mac.

Responsibilities:

- audio/video upload,
- automatic codec/format detection,
- high-quality transcription,
- speaker diarization,
- segment timestamps,
- silence detection and preservation,
- optional word-level timing/alignment,
- real-time processing progress,
- transcript review/edit,
- speaker rename,
- export,
- local persistence,
- sync completed interview to cloud workspace.

### 3.2 Cloud Interview Workspace

Always online even when the Mac is off.

Responsibilities:

- browse interviews by company/date,
- playback synced audio,
- view transcript,
- search transcript,
- view speaker timeline,
- view processing metadata,
- download/export files,
- generate controlled share links,
- prepare for future AI review.

---

## 4. Naming and File Organization

Keep naming deliberately simple.

### 4.1 Required metadata

- Company name
- Recruiter/interviewer name
- Recording timestamp
- Sequential recording number

### 4.2 Base filename

```text
YYYY-MM-DD_HHMM_recruiter-name_01
YYYY-MM-DD_HHMM_recruiter-name_02
YYYY-MM-DD_HHMM_recruiter-name_03
```

All generated files for the same recording share the exact same base filename.

Example:

```text
2026-08-21_1615_rahul_01.m4a
2026-08-21_1615_rahul_01.json
2026-08-21_1615_rahul_01.srt
2026-08-21_1615_rahul_01.md
2026-08-21_1615_rahul_01.txt
```

### 4.3 Company hierarchy

```text
recordings/
  navi/
    2026-08-21_1615_rahul_01/
      2026-08-21_1615_rahul_01.m4a
      2026-08-21_1615_rahul_01.json
      2026-08-21_1615_rahul_01.srt
      2026-08-21_1615_rahul_01.md
      metadata.json
```

### 4.4 Company detection

Company detection is assistive, not authoritative.

Sources may include:

- filename,
- explicit company field,
- known vocabulary,
- early transcript content.

UI behavior:

```text
Detected company: Navi
[Confirm] [Change]
```

No destructive automatic renaming without confirmation.

---

## 5. Functional Requirements

### FR-1 Audio/video ingestion

Support at minimum:

- WAV
- MP3
- AAC
- M4A
- MP4 audio track

Use `ffprobe` to detect:

- codec,
- sample rate,
- channels,
- duration,
- bitrate,
- container.

The user should not manually choose a conversion format.

### FR-2 Audio preprocessing

Pipeline:

```text
Input
  -> ffprobe
  -> decide whether direct decode is supported
  -> FFmpeg normalization only when needed
  -> transcription-ready audio representation
```

Pydub should not be the central audio abstraction in the new architecture.

### FR-3 Transcription

Reference engine:

- MLX Whisper
- `large-v3`

Requirements:

- highest practical accuracy,
- segment timestamps,
- language metadata,
- deterministic artifact generation,
- support model benchmarking without coupling UI to model implementation.

### FR-4 Speaker diarization

Speaker diarization is mandatory for V1.

Output example:

```text
[00:13:42 - 00:14:10] Interviewer
Can you walk me through the architecture?

[00:14:10 - 00:14:26] SILENCE - 16 sec

[00:14:26 - 00:17:51] You
Sure. The system was...
```

Users must be able to rename speakers.

### FR-5 Silence preservation

Silence may be skipped for inference optimization but must never be removed from the absolute interview timeline.

Silence data must be persisted:

```json
{
  "start": 843.2,
  "end": 878.5,
  "type": "silence",
  "duration": 35.3
}
```

This enables later analysis of thinking time, pauses, interruptions, and time spent per section.

### FR-6 Word timestamps

Three timing concepts must remain separate:

1. segment timestamps — mandatory,
2. speaker timestamps — mandatory,
3. word timestamps — optional processing stage.

Word timestamps should be retained where useful for exact word-seek/highlighting, but the system must benchmark whether alignment can happen after primary transcription so transcription latency is not unnecessarily increased.

### FR-7 Real-time processing status

The local UI must show actual stage-level progress.

Example:

```text
Preparing audio        ✓  00:04
Speech detection       ✓  00:09
Transcribing          67%  08:21
Speaker detection      Waiting
Alignment              Waiting
Export                 Waiting
Cloud sync             Waiting

Audio processed:       58:31 / 1:27:42
Elapsed:               08:34
Realtime factor:       0.147
Estimated remaining:   04:11
```

Progress must be derived from measurable work, not hard-coded model speed constants.

### FR-8 Transcript editing

V1 should support:

- search,
- transcript text editing,
- speaker rename,
- timestamp navigation,
- copy,
- export.

### FR-9 Local library

Persist interviews locally in SQLite.

Users should be able to browse prior jobs without scanning loose JSON files.

### FR-10 Cloud sync

After local completion, the user can sync the interview to the cloud workspace.

Artifacts:

- source audio,
- transcript JSON,
- SRT,
- Markdown,
- metadata.

### FR-11 Cloud viewer

Must work while the Mac is off.

The hosted viewer should support:

- company-based navigation,
- interview list,
- transcript reading,
- audio playback,
- timestamp seeking,
- speaker labels,
- search,
- downloads,
- share links.

---

## 6. Future AI Review — Explicitly In Scope for Architecture

AI review is not required for the first transcription milestone, but V1 architecture must make it a first-class future capability.

### 6.1 User experience goal

From a completed interview:

```text
[ Review Interview ]
```

One click should:

1. prepare the transcript and metadata,
2. send them to the configured AI provider,
3. apply a structured evaluation rubric,
4. return an interview review.

The user should no longer need to manually upload transcripts into separate AI chats.

### 6.2 Supported provider architecture

Create a provider-neutral interface.

```python
class InterviewReviewProvider:
    def review(self, request: InterviewReviewRequest) -> InterviewReviewResult:
        ...
```

Future implementations:

```text
OpenAIReviewProvider
GeminiReviewProvider
ClaudeReviewProvider
LocalLLMReviewProvider
CustomProvider
```

The domain layer must not depend directly on OpenAI, Google, or Anthropic SDKs.

### 6.3 Review request model

```json
{
  "company": "Navi",
  "role": "Engineering Manager",
  "target_level": "EM / Senior EM",
  "round_type": "System Design",
  "transcript": "...",
  "segments": [],
  "speakers": [],
  "timing": {},
  "candidate_context": {},
  "evaluation_profile": "engineering_manager_system_design_v1"
}
```

### 6.4 Expected AI output

At minimum:

```json
{
  "summary": "...",
  "overall_rating": 7.8,
  "likely_outcome": "borderline_positive",
  "role_level_fit": "EM",
  "strengths": [],
  "growth_areas": [],
  "questions": [],
  "answer_reviews": [],
  "section_reviews": [],
  "time_analysis": {},
  "communication": {},
  "technical_depth": {},
  "leadership": {},
  "product_thinking": {},
  "recommended_practice": []
}
```

### 6.5 Expected rating disclaimer

Predicted interview outcome and role/level fit are probabilistic AI assessments, not factual hiring decisions. The UI must present them as estimates.

### 6.6 Cross-interview feedback loop

Future analytics should aggregate multiple reviews to answer:

- Which areas repeatedly score low?
- Which interview types fail most often?
- Is communication improving over time?
- Is the candidate spending too long on requirements or HLD?
- Which follow-up questions repeatedly expose gaps?
- Which strengths consistently appear?
- How does performance differ by company or role type?

This is the core long-term value proposition of Interview IntelliSense.

---

## 7. Non-Functional Requirements

### NFR-1 Accuracy

Accuracy is the primary optimization constraint.

No faster model becomes default unless measured on a representative interview benchmark set and shown to have no material quality degradation.

### NFR-2 Performance

Optimize:

- decode time,
- silence handling,
- GPU utilization,
- diarization latency,
- word alignment latency,
- output generation,
- upload time.

Do not equate CPU core count with Whisper inference parallelism.

### NFR-3 Reliability

- jobs survive UI refresh,
- failed jobs can be retried,
- process restart does not corrupt state,
- outputs are job-scoped,
- no filename collisions,
- no process-global stderr suppression.

### NFR-4 Security

- no secrets committed,
- `.env.example` only,
- private-by-default cloud storage,
- controlled share links,
- provider API keys stored locally/server-side,
- AI review requires explicit provider configuration.

### NFR-5 Responsiveness

Local and cloud UIs must work cleanly on desktop and narrower browser widths.

### NFR-6 Observability

Record per-job metrics:

```json
{
  "audio_duration_sec": 5422,
  "probe_sec": 0.3,
  "decode_sec": 4.8,
  "vad_sec": 8.2,
  "transcription_sec": 713.4,
  "diarization_sec": 95.1,
  "alignment_sec": 82.1,
  "export_sec": 0.4,
  "cloud_sync_sec": 21.0,
  "realtime_factor": 0.17
}
```

---

## 8. High-Level Architecture

```text
                    LOCAL MAC

              Transcript Studio UI
                       |
                       v
                    FastAPI
                       |
                 Application Layer
                       |
      +----------------+----------------+
      |                |                |
      v                v                v
 Audio Pipeline   Transcription     Job Service
      |             Engine             |
      |                |                |
      |           MLX Whisper           |
      |                |                |
      +---------> Diarization <---------+
                       |
                       v
                  Transcript
                       |
            +----------+----------+
            |                     |
            v                     v
          SQLite              Local Files
            |
            +------ Sync Service ------+
                                      |
                                      v

                        CLOUD

                   Cloudflare R2
                 audio / artifacts
                         |
                         v
                 Cloudflare-hosted
                 Interview Workspace
                         |
                         v
                   Browser / Share
```

---

## 9. Proposed Repository Structure

```text
interview-intellisense/
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
│
├── docs/
│   ├── PRODUCT.md
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── TRANSCRIPTION_PIPELINE.md
│   ├── DATA_MODEL.md
│   ├── PERFORMANCE.md
│   ├── CLOUD_SYNC.md
│   ├── AI_REVIEW.md
│   ├── TESTING.md
│   ├── ROADMAP.md
│   └── adr/
│
├── apps/
│   ├── local_api/
│   ├── local_ui/
│   └── web_viewer/
│
├── interview_intellisense/
│   ├── domain/
│   ├── services/
│   ├── engines/
│   ├── audio/
│   ├── diarization/
│   ├── repositories/
│   ├── workers/
│   ├── exporters/
│   ├── cloud/
│   ├── ai_review/
│   └── config/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── benchmarks/
│
├── scripts/
└── .github/
    └── workflows/
```

---

## 10. Core Interfaces

### 10.1 Transcription engine

```python
class TranscriptionEngine(Protocol):
    def transcribe(self, request: TranscriptionRequest) -> Transcript:
        ...
```

Implementations:

- `MLXWhisperEngine`
- future `FasterWhisperEngine`
- future cloud engine

### 10.2 Diarization engine

```python
class DiarizationEngine(Protocol):
    def diarize(self, audio: AudioAsset) -> DiarizationResult:
        ...
```

### 10.3 Storage repository

```python
class InterviewRepository(Protocol):
    def save(...): ...
    def get(...): ...
    def list(...): ...
```

### 10.4 Cloud storage

```python
class CloudArtifactStore(Protocol):
    def upload(...): ...
    def create_share_link(...): ...
```

### 10.5 AI review

```python
class InterviewReviewProvider(Protocol):
    def review(...): ...
```

---

## 11. SQLite Data Model — Initial

### interviews

```text
id
company
recruiter_name
role
round_type
recorded_at
sequence_number
status
duration_sec
source_path
created_at
updated_at
```

### artifacts

```text
id
interview_id
type
local_path
cloud_key
mime_type
size_bytes
created_at
```

### transcript_segments

```text
id
interview_id
start_ms
end_ms
speaker_id
segment_type
text
```

`segment_type`:

- speech
- silence

### speakers

```text
id
interview_id
raw_label
display_name
role
```

### job_metrics

```text
interview_id
stage
started_at
completed_at
duration_ms
metadata_json
```

### ai_reviews — future-compatible

```text
id
interview_id
provider
model
evaluation_profile
status
result_json
created_at
```

---

## 12. Vocabulary Profiles

V1 should include a built-in Staff/EM engineering vocabulary profile.

Categories:

- distributed systems,
- databases,
- messaging,
- availability/reliability,
- performance,
- architecture,
- operational excellence,
- leadership,
- prioritization,
- stakeholder management,
- product thinking.

Example terms:

```text
Kafka
SQS
SNS
DynamoDB
PostgreSQL
Redis
CDC
Debezium
idempotency
P99
SLA
SLO
backpressure
sharding
leader election
HLD
LLD
operational excellence
trade-offs
```

Company-specific vocabulary may enrich this profile after company confirmation.

---

## 13. Performance Strategy

### 13.1 Measure first

Benchmark representative 60–90 minute interviews.

Capture:

- total runtime,
- stage runtime,
- real-time factor,
- transcription errors,
- proper nouns,
- technical terminology,
- speaker assignment errors,
- timestamp quality.

### 13.2 Model policy

`large-v3` remains default.

Alternative models may only replace it after passing the benchmark corpus under a defined quality threshold.

### 13.3 CPU/GPU utilization

Use CPU cores for parallelizable peripheral stages:

- ffprobe/FFmpeg,
- VAD,
- metadata,
- exports,
- diarization preprocessing,
- cloud upload.

Use MLX GPU path for transcription.

Benchmark inference parallelism at 1, 2, and 4 chunks before considering higher concurrency.

### 13.4 Chunking

If chunking is introduced:

- preserve absolute timestamps,
- overlap boundaries,
- carry context,
- avoid speaker fragmentation,
- validate transcript continuity.

---

## 14. Local Runtime Strategy

Use native Python rather than Docker for the Apple MLX worker.

Recommended:

```text
Python
uv
MLX
FFmpeg
SQLite
FastAPI
```

Why:

- direct Apple Silicon integration,
- simpler local audio access,
- lower MLX friction,
- better local performance.

Docker remains useful for:

- CI,
- hosted web services,
- future cloud workers,
- reproducible non-MLX components.

---

## 15. Cloud Strategy

### Initial target

- Cloudflare R2 for private audio/transcript artifact storage.
- Cloudflare-hosted web viewer for always-online access.

The cloud workspace must remain useful even when the local Mac is powered off.

### Privacy

Default state:

```text
Private interview
```

Optional:

```text
Create share link
```

Future:

- expiring links,
- password-protected shares,
- revoke share.

---

## 16. UI Direction — Locked

### Local UI

Use **Transcript Studio** style:

- polished drag/drop upload,
- compact interview metadata,
- visible processing state,
- transcript-first result view,
- waveform/player,
- speaker labels,
- search/edit/export/share.

### Cloud UI

Use **Interview Workspace** style:

- dashboard/library,
- company navigation,
- interview history,
- transcript viewer,
- audio playback,
- metadata,
- future analytics and AI review.

Goal: production-grade visual quality without spending disproportionate engineering time. Use modern component libraries and AI-assisted frontend implementation.

---

## 17. Testing Strategy

### Unit tests

- filename generation,
- audio metadata parsing,
- silence segment creation,
- transcript merging,
- exporter behavior,
- repository behavior,
- provider adapters.

### Integration tests

- upload -> transcribe -> persist,
- transcribe -> diarize -> merge,
- crash/retry,
- sync -> cloud metadata,
- transcript reload.

### Benchmark tests

Maintain a private benchmark corpus covering:

- clean recruiter calls,
- noisy calls,
- Indian accents,
- US accents,
- system design interviews,
- coding interviews,
- multiple speakers,
- technical jargon,
- long silences.

Do not commit private interview audio to the public GitHub repository.

---

## 18. GitHub / Open-Source Readiness

The repository should include:

- strong README,
- architecture diagram,
- setup instructions,
- sample transcript fixtures,
- `.env.example`,
- license,
- `uv.lock`,
- GitHub Actions,
- testing instructions,
- benchmark methodology,
- screenshots/GIFs,
- roadmap,
- contribution guide,
- ADRs.

No private recordings, recruiter information, or API tokens may be committed.

---

## 19. P0 Execution Order

All items below are P0 for the first serious release, executed in dependency order.

1. New repository structure and documentation
2. Core domain models and interfaces
3. Audio detection / FFmpeg pipeline
4. MLX Whisper large-v3 engine
5. Performance instrumentation
6. Speaker diarization
7. VAD and silence timeline preservation
8. Staff/EM vocabulary profiles
9. SQLite persistence
10. Job queue and crash recovery
11. FastAPI local backend
12. Lock local Transcript Studio UI
13. Implement local UI
14. Cloudflare artifact sync
15. Lock cloud Interview Workspace UI
16. Implement hosted viewer
17. Tests and CI
18. GitHub packaging/docs
19. AI review provider interfaces and storage schema
20. One-click AI review implementation in a later iteration

---

## 20. AI-Accelerated Delivery Plan

The goal is not to spend 3–4 calendar weeks manually writing everything.

Use AI to accelerate:

- boilerplate generation,
- test generation,
- component scaffolding,
- API schemas,
- docs,
- migrations,
- refactors,
- frontend implementation,
- benchmark report generation.

Human review remains mandatory for:

- architecture decisions,
- transcription quality,
- diarization quality,
- performance measurements,
- privacy/security decisions,
- AI evaluation rubric quality.

A realistic target with focused AI-assisted development is to compress the first usable production-grade version into roughly **7–12 focused development days**, followed by iterative quality tuning against real recordings.

---

## 21. Definition of Done — V1 Foundation

V1 foundation is complete when:

- a 60–90 minute interview can be uploaded locally,
- format is detected automatically,
- transcription uses large-v3,
- speakers are separated,
- silence remains represented in the timeline,
- stage-level progress is visible,
- transcript is editable/searchable,
- results persist in SQLite,
- outputs use the agreed filename convention,
- completed interviews can sync to cloud storage,
- cloud viewer works with the Mac turned off,
- tests cover core logic,
- repo setup is reproducible,
- no secrets/private recordings are committed,
- architecture is ready for one-click OpenAI/Gemini/Claude review.

---

## 22. Future Product Direction

The long-term loop is:

```text
Record interview
   -> transcribe locally
   -> diarize
   -> understand timing
   -> review with AI
   -> score the round
   -> identify strengths
   -> identify growth areas
   -> compare against prior rounds
   -> generate targeted practice plan
   -> improve next interview
```

That feedback loop — not transcription alone — is the product.
