import argparse
import json
from pathlib import Path

from interview_intelligence.diarization.aligner import SpeakerAligner
from interview_intelligence.diarization.models import SpeakerTurn
from interview_intelligence.domain.models import TranscriptSegment


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Align pyannote speaker turns with timestamped transcript segments."
    )
    parser.add_argument("segments_json", type=Path)
    parser.add_argument("speaker_turns_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    segments_raw = json.loads(args.segments_json.read_text(encoding="utf-8"))
    turns_raw = json.loads(args.speaker_turns_json.read_text(encoding="utf-8"))

    segments = [TranscriptSegment.model_validate(item) for item in segments_raw]
    turns = [SpeakerTurn.model_validate(item) for item in turns_raw]

    aligned = SpeakerAligner().align(segments, turns)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "aligned_segments.json"
    json_path.write_text(
        json.dumps(
            [segment.model_dump(mode="json") for segment in aligned],
            indent=2,
        ),
        encoding="utf-8",
    )

    transcript_path = output_dir / "aligned_transcript.txt"
    lines = []
    for segment in aligned:
        speaker = segment.speaker_id or "UNKNOWN"
        lines.append(
            f"[{format_timestamp(segment.start_seconds)} -> "
            f"{format_timestamp(segment.end_seconds)}] "
            f"{speaker}: {segment.text}"
        )

    transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assigned = sum(1 for segment in aligned if segment.speaker_id is not None)
    payload = {
        "segment_count": len(aligned),
        "speaker_assigned_count": assigned,
        "speaker_assignment_rate": round(
            assigned / len(aligned) if aligned else 0.0,
            4,
        ),
        "aligned_segments_path": str(json_path),
        "aligned_transcript_path": str(transcript_path),
    }

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
