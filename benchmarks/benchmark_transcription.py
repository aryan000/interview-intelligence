import argparse
import json
import time
from pathlib import Path

from interview_intelligence.audio.inspector import FFprobeAudioInspector
from interview_intelligence.audio.preparer import FFmpegAudioPreparer
from interview_intelligence.engines.base import TranscriptionRequest
from interview_intelligence.engines.mlx_whisper import MLXWhisperEngine
from interview_intelligence.engines.vocabulary import build_interview_prompt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the Interview Intelligence MLX transcription pipeline."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for temporary prepared audio and benchmark artifacts.",
    )
    parser.add_argument(
        "--model",
        default="mlx-community/whisper-large-v3-mlx",
    )
    parser.add_argument("--company")
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Enable Whisper word-level timestamps for this benchmark.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source = args.source.expanduser().resolve()
    prepared_path = output_dir / f"{source.stem}_prepared.wav"

    total_started = time.perf_counter()

    inspector = FFprobeAudioInspector()
    preparer = FFmpegAudioPreparer(inspector)
    preparation = preparer.prepare(source, prepared_path)

    prompt = build_interview_prompt(company=args.company)
    engine = MLXWhisperEngine(model_repo=args.model)

    transcription_started = time.perf_counter()
    result = engine.transcribe(
        TranscriptionRequest(
            audio_path=prepared_path,
            initial_prompt=prompt,
            word_timestamps=args.word_timestamps,
        )
    )
    transcription_seconds = time.perf_counter() - transcription_started
    total_seconds = time.perf_counter() - total_started

    transcript_path = output_dir / f"{source.stem}_transcript.txt"
    transcript_path.write_text(result.text + "\n", encoding="utf-8")

    segments_path = output_dir / f"{source.stem}_segments.json"
    segments_payload = [
        segment.model_dump(mode="json") for segment in result.segments
    ]
    segments_path.write_text(
        json.dumps(segments_payload, indent=2),
        encoding="utf-8",
    )

    audio_duration = preparation.prepared.duration_seconds
    metrics = {
        "source_path": str(source),
        "prepared_path": str(preparation.output_path),
        "model": result.model_name,
        "engine": result.engine_name,
        "language": result.language,
        "word_timestamps": args.word_timestamps,
        "source_duration_seconds": preparation.source.duration_seconds,
        "prepared_duration_seconds": audio_duration,
        "preparation_seconds": round(preparation.elapsed_seconds, 3),
        "transcription_seconds": round(transcription_seconds, 3),
        "total_pipeline_seconds": round(total_seconds, 3),
        "transcription_realtime_factor": round(
            transcription_seconds / audio_duration,
            6,
        ),
        "total_realtime_factor": round(
            total_seconds / audio_duration,
            6,
        ),
        "segment_count": len(result.segments),
        "preparation_warnings": list(preparation.warnings),
        "transcript_path": str(transcript_path),
        "segments_path": str(segments_path),
    }

    metrics_path = output_dir / f"{source.stem}_benchmark.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
