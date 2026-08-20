import argparse
import json
import time
from pathlib import Path

from interview_intelligence.audio.inspector import FFprobeAudioInspector
from interview_intelligence.audio.preparer import FFmpegAudioPreparer
from interview_intelligence.engines.mlx_whisper import MLXWhisperEngine
from interview_intelligence.engines.vocabulary import build_interview_prompt
from interview_intelligence.transcription.chunking import FixedWindowChunker
from interview_intelligence.transcription.runner import (
    ChunkedTranscriptionRunner,
    ChunkProgress,
)


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def print_progress(progress: ChunkProgress) -> None:
    print(
        f"[{progress.percent:5.1f}%] "
        f"chunk {progress.completed_chunks}/{progress.total_chunks} | "
        f"audio {format_duration(progress.processed_audio_seconds)}"
        f"/{format_duration(progress.total_audio_seconds)} | "
        f"elapsed {format_duration(progress.elapsed_seconds)} | "
        f"ETA {format_duration(progress.estimated_remaining_seconds)}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark progress-aware chunked MLX transcription."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--company")
    parser.add_argument("--chunk-seconds", type=float, default=600.0)
    parser.add_argument(
        "--model",
        default="mlx-community/whisper-large-v3-mlx",
    )
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_path = output_dir / f"{source.stem}_canonical.wav"
    inspector = FFprobeAudioInspector()
    preparer = FFmpegAudioPreparer(inspector)

    print("Preparing canonical audio...", flush=True)
    total_started = time.perf_counter()
    preparation = preparer.prepare(source, canonical_path)
    print(
        f"Prepared {format_duration(preparation.prepared.duration_seconds)} "
        f"in {preparation.elapsed_seconds:.2f}s",
        flush=True,
    )

    engine = MLXWhisperEngine(model_repo=args.model)
    runner = ChunkedTranscriptionRunner(
        engine,
        chunker=FixedWindowChunker(args.chunk_seconds),
    )

    print(
        f"Transcribing in {args.chunk_seconds:.0f}s sequential chunks...",
        flush=True,
    )
    result = runner.run(
        canonical_audio_path=canonical_path,
        duration_seconds=preparation.prepared.duration_seconds,
        work_dir=output_dir / "chunks",
        initial_prompt=build_interview_prompt(company=args.company),
        progress_listener=print_progress,
    )

    total_seconds = time.perf_counter() - total_started

    transcript_path = output_dir / f"{source.stem}_chunked_transcript.txt"
    transcript_path.write_text(result.text + "\n", encoding="utf-8")

    segments_path = output_dir / f"{source.stem}_chunked_segments.json"
    segments_path.write_text(
        json.dumps(
            [segment.model_dump(mode="json") for segment in result.segments],
            indent=2,
        ),
        encoding="utf-8",
    )

    metrics = {
        "source": str(source),
        "model": args.model,
        "chunk_seconds": args.chunk_seconds,
        "chunk_count": result.chunk_count,
        "audio_duration_seconds": preparation.prepared.duration_seconds,
        "preparation_seconds": round(preparation.elapsed_seconds, 3),
        "transcription_seconds": round(result.elapsed_seconds, 3),
        "total_pipeline_seconds": round(total_seconds, 3),
        "transcription_realtime_factor": round(
            result.elapsed_seconds / preparation.prepared.duration_seconds,
            6,
        ),
        "segment_count": len(result.segments),
        "transcript_path": str(transcript_path),
        "segments_path": str(segments_path),
    }

    metrics_path = output_dir / f"{source.stem}_chunked_benchmark.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\nBenchmark complete:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
