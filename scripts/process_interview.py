import argparse
import json
from datetime import datetime
from pathlib import Path

from interview_intelligence.application.services import (
    build_local_processing_pipeline,
)
from interview_intelligence.pipeline.models import InterviewProcessingRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the complete local Interview Intelligence pipeline."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--company", required=True)
    parser.add_argument("--person", required=True)
    parser.add_argument(
        "--interview-datetime",
        required=True,
        help="ISO 8601 local datetime, e.g. 2026-07-30T12:00:00",
    )
    parser.add_argument("--sequence", type=int, default=1)
    parser.add_argument("--role")
    parser.add_argument("--target-level")
    parser.add_argument("--num-speakers", type=int, default=2)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path.home() / "Interview Intelligence",
    )
    args = parser.parse_args()

    request = InterviewProcessingRequest(
        source_audio=args.source.expanduser().resolve(),
        company=args.company,
        recruiter_or_interviewer=args.person,
        sequence_number=args.sequence,
        interview_datetime=datetime.fromisoformat(args.interview_datetime),
        role=args.role,
        target_level=args.target_level,
        num_speakers=args.num_speakers,
    )

    pipeline = build_local_processing_pipeline(args.output_root)
    result = pipeline.process(request)

    summary = {
        "artifacts": result.artifacts.model_dump(mode="json"),
        "segment_count": len(result.segments),
        "quality_issue_count": len(result.quality_issues),
        "candidate_speaker_id": result.candidate_speaker_id,
        "interviewer_speaker_id": result.interviewer_speaker_id,
        "speaker_mapping_confidence": result.speaker_mapping_confidence,
        "transcription_seconds": round(result.transcription_seconds, 3),
        "diarization_seconds": round(result.diarization_seconds, 3),
        "total_seconds": round(result.total_seconds, 3),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
