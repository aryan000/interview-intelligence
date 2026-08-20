import argparse
import json
import os
import time
from pathlib import Path

from interview_intelligence.audio.inspector import FFprobeAudioInspector
from interview_intelligence.audio.preparer import FFmpegAudioPreparer
from interview_intelligence.diarization.pyannote_engine import (
    PyannoteDiarizationEngine,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark local pyannote speaker diarization."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-speakers", type=int, default=2)
    parser.add_argument(
        "--model",
        default="pyannote/speaker-diarization-community-1",
    )
    parser.add_argument(
        "--device",
        choices=["mps", "cpu"],
        default=None,
    )
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    inspector = FFprobeAudioInspector()
    canonical_path = output_dir / f"{source.stem}_canonical.wav"
    preparation = FFmpegAudioPreparer(inspector).prepare(source, canonical_path)

    token = os.getenv("HF_TOKEN")
    engine = PyannoteDiarizationEngine(
        model_name=args.model,
        token=token,
        device=args.device,
    )

    print(
        f"Diarizing {preparation.prepared.duration_seconds:.1f}s "
        f"on {engine.device}...",
        flush=True,
    )

    started = time.perf_counter()
    result = engine.diarize(
        canonical_path,
        num_speakers=args.num_speakers,
    )
    elapsed = time.perf_counter() - started

    turns_path = output_dir / f"{source.stem}_speaker_turns.json"
    turns_path.write_text(
        json.dumps(
            [turn.model_dump(mode="json") for turn in result.turns],
            indent=2,
        ),
        encoding="utf-8",
    )

    metrics = {
        "source": str(source),
        "model": result.model_name,
        "device": engine.device,
        "audio_duration_seconds": preparation.prepared.duration_seconds,
        "diarization_seconds": round(elapsed, 3),
        "realtime_factor": round(
            elapsed / preparation.prepared.duration_seconds,
            6,
        ),
        "speaker_count": result.speaker_count,
        "turn_count": len(result.turns),
        "turns_path": str(turns_path),
    }

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
