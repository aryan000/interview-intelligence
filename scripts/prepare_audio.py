import argparse
import json
from pathlib import Path

from interview_intelligence.audio.inspector import FFprobeAudioInspector
from interview_intelligence.audio.preparer import FFmpegAudioPreparer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize an interview recording to canonical 16 kHz mono PCM WAV."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    preparer = FFmpegAudioPreparer(FFprobeAudioInspector())
    result = preparer.prepare(args.source, args.output)

    payload = {
        "source": result.source.model_dump(mode="json"),
        "prepared": result.prepared.model_dump(mode="json"),
        "output_path": str(result.output_path),
        "elapsed_seconds": round(result.elapsed_seconds, 3),
        "warnings": list(result.warnings),
        "duration_delta_seconds": round(
            result.source.duration_seconds - result.prepared.duration_seconds,
            3,
        ),
        "preprocessing_realtime_factor": round(
            result.elapsed_seconds / result.prepared.duration_seconds,
            6,
        ),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
