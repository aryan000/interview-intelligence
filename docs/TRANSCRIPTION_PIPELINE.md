# Transcription Pipeline

## Goal

Produce the highest practical transcription quality while minimizing processing time without reducing accuracy.

The pipeline must preserve:

- original timeline
- speaker information
- silence intervals
- segment timestamps
- optional word timestamps

## Pipeline

```text
Input Recording
      │
      ▼
Audio Inspection
      │
      ▼
Format Decision
      │
      ├── supported directly ────────┐
      │                              │
      └── normalization required     │
                  │                  │
                  ▼                  │
               FFmpeg                │
                  │                  │
                  └──────────────────┘
                          │
                          ▼
                  Speech / Silence Analysis
                          │
                          ▼
                    Transcription
                    MLX large-v3
                          │
                          ▼
                     Diarization
                          │
                          ▼
                   Timeline Alignment
                          │
                          ▼
                 Transcript Generation
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
            JSON          SRT          Markdown
                          │
                          ▼
                    Local Persistence
                          │
                          ▼
                   Optional Cloud Sync
```

## Stage 1: Audio Inspection

Use ffprobe to detect:

- container
- codec
- duration
- sample rate
- channels
- bitrate
- file size

Example internal metadata:

```json
{
  "format": "aac",
  "codec": "aac",
  "duration_seconds": 5234.1,
  "sample_rate": 48000,
  "channels": 2
}
```

## Stage 2: Format Decision

Conversion must not happen automatically merely because the input is AAC, M4A, MP3, or WAV.

The system should determine whether the transcription engine can consume the input directly.

Only normalize when required.

If normalization is needed, use FFmpeg rather than loading the entire audio file through a high-level Python audio abstraction.

## Stage 3: Speech and Silence Detection

Voice Activity Detection may be used to reduce unnecessary inference.

Important distinction:

```text
Skip silence for model inference
does not mean
delete silence from the timeline.
```

Silence intervals must remain available in metadata.

Example:

```json
{
  "type": "silence",
  "start": 843.2,
  "end": 868.4,
  "duration": 25.2
}
```

This enables future analysis of:

- thinking time
- long pauses
- interview pacing
- coding silence
- question-response latency

## Stage 4: Transcription

Initial reference engine:

MLX Whisper large-v3

Reason:

Maximum practical transcription accuracy is the primary requirement.

Other models may be benchmarked, but no alternative becomes the default unless it demonstrates equivalent practical accuracy on representative interview recordings.

## Interview Vocabulary Context

Transcription should support an initial prompt/context profile.

Default profile:

Staff / Engineering Manager software engineering interviews.

Example vocabulary:

- Kafka
- Redis
- DynamoDB
- PostgreSQL
- CDC
- Debezium
- idempotency
- sharding
- replication
- backpressure
- P99
- SLA
- SLO
- HLD
- LLD
- operational excellence
- stakeholder management

Company/domain-specific vocabulary may be added dynamically.

## Stage 5: Speaker Diarization

Speaker diarization is mandatory.

Output should initially use neutral speaker identifiers:

```text
SPEAKER_01
SPEAKER_02
```

The user may rename these:

```text
SPEAKER_01 → Interviewer
SPEAKER_02 → Candidate
```

## Stage 6: Timeline Alignment

Transcript segments, diarization turns, and silence intervals must be aligned to the original audio clock.

Example:

```text
[00:13:42 - 00:14:10] Interviewer
Can you walk me through the architecture?

[00:14:10 - 00:14:26] SILENCE - 16 sec

[00:14:26 - 00:17:51] Candidate
Sure. The system was...
```

## Timestamp Levels

### Segment timestamps

Required.

Used for:

- interview timing analysis
- transcript navigation
- AI feedback
- section duration analysis

### Speaker timestamps

Required.

Used for:

- speaking-time calculations
- interruptions
- question/answer duration

### Word timestamps

Supported but separable.

Used for:

- exact word seeking
- audio highlighting
- karaoke-style playback

Word alignment should be benchmarked independently to understand its performance cost.

## Real-Time Progress

Progress must represent actual pipeline stages.

Example:

```text
Inspecting audio       complete
Preparing audio        complete
Detecting speech       complete
Transcribing           67%
Diarization            waiting
Alignment              waiting
Export                  waiting
Cloud sync              waiting
```

Metrics should include:

- audio seconds processed
- elapsed time
- total audio duration
- real-time factor
- estimated remaining time

## Performance Metrics

Each job should capture:

```text
audio_duration_seconds
inspection_duration_seconds
preprocessing_duration_seconds
vad_duration_seconds
transcription_duration_seconds
diarization_duration_seconds
alignment_duration_seconds
export_duration_seconds
cloud_sync_duration_seconds
total_duration_seconds
realtime_factor
```

## CPU/GPU Strategy

Apple Silicon environment:

- Apple M5
- 32 GB unified memory
- 10 CPU cores
- 10 GPU cores

Do not assume that ten CPU cores imply ten parallel Whisper workers.

Preferred approach:

```text
CPU
├── FFmpeg
├── ffprobe
├── VAD
├── metadata processing
├── exports
└── cloud upload

GPU
└── MLX Whisper inference
```

Chunk parallelism must be benchmarked at controlled concurrency levels such as:

- 1
- 2
- 4

Quality and throughput must both be measured.

## Benchmark Policy

Performance optimization must be evidence-based.

Representative recordings should include:

- recruiter calls
- system design interviews
- coding interviews
- noisy recordings
- multiple speakers
- Indian accents
- international accents
- technical vocabulary
- long silence periods

large-v3 is the accuracy baseline.

Any optimization must be compared against that baseline.
