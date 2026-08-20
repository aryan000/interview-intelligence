# ADR-001: Use Native MLX for Local Transcription

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

The primary transcription environment is an Apple Mac with an M5 chip, 32 GB unified memory, 10 CPU cores, and 10 GPU cores.

Transcription quality is the primary constraint. Performance should be optimized only where accuracy is not materially reduced.

The existing prototype already uses MLX Whisper successfully on Apple Silicon.

## Decision

The V1 local transcription worker will run natively on macOS using Python and MLX rather than inside Docker.

`MLXWhisperEngine` will be the initial implementation of a generic `TranscriptionEngine` interface.

Whisper large-v3 will remain the reference transcription model until another model demonstrates equivalent practical accuracy on the representative interview benchmark corpus.

The Python environment will use `uv` with a committed lockfile for reproducibility.

## Consequences

### Positive

- Direct access to Apple Silicon acceleration.
- Avoids container-related GPU/Metal limitations and complexity.
- Best fit for the target hardware.
- Keeps local inference private and offline-capable.
- MLX implementation remains replaceable through an engine interface.

### Negative

- Local worker is macOS/Apple-Silicon-oriented.
- Native dependencies such as FFmpeg must be installed on the host.
- Reproducibility depends on environment setup rather than a single Docker image.

## Alternatives Considered

### Dockerized MLX worker

Rejected for V1 because containerization adds complexity without improving the primary local inference workload.

### Cloud GPU transcription

Rejected as the default because it adds recurring cost, network dependency, and privacy concerns.

### CPU-only Whisper

Rejected because it does not make effective use of the target Apple Silicon hardware.

## Follow-up

Benchmark large-v3 and any candidate alternatives against the same interview corpus before changing the default model.
