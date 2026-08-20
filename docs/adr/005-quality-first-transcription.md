# ADR-005: Optimize Transcription for Quality First

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Interview transcripts are used for detailed review and future AI evaluation.

Incorrect technical terms, missed statements, speaker errors, or broken timing can lead to incorrect feedback.

Faster transcription is valuable, especially for 60–90 minute interviews, but not at the cost of meaningful accuracy.

## Decision

Transcription quality is a hard constraint.

MLX Whisper large-v3 is the initial accuracy reference.

Performance optimizations are accepted only when they preserve practical output quality on the representative interview benchmark corpus.

Optimization work should first target:

- unnecessary audio conversion
- FFmpeg/ffprobe efficiency
- silence-aware inference
- preprocessing
- caching
- CPU/GPU pipelining
- diarization efficiency
- timestamp/alignment architecture
- controlled concurrency

Alternative models such as Turbo may be benchmarked but must not become the default solely because they are faster.

## Timestamp Policy

Segment timestamps are mandatory.

Speaker timing is mandatory.

Silence may be skipped for inference but must remain represented in the original timeline.

Word timestamps are required when exact word-level playback/highlighting is enabled, but their generation should be architecturally separable and independently benchmarked.

## Consequences

### Positive

- AI feedback is grounded in the best available transcript.
- Performance changes are evidence-based.
- Prevents silent quality regression.
- Establishes a repeatable benchmark methodology.

### Negative

- Some speed optimizations will be rejected.
- Benchmarking takes additional engineering effort.
- Highest-quality models may require longer processing times.

## Benchmark Corpus

Representative recordings should cover:

- recruiter calls
- Engineering Manager interviews
- Staff-level interviews
- system design
- coding
- leadership discussions
- multiple speakers
- Indian and international accents
- noisy audio
- technical vocabulary
- long pauses

## Follow-up

Record stage-level timings and quality results for every performance experiment so optimization decisions remain reproducible.
