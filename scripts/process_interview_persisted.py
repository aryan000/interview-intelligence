import argparse
import json
from datetime import datetime
from pathlib import Path

from interview_intelligence.application.coordinator import (
    InterviewProcessingCoordinator,
)
from interview_intelligence.application.services import build_local_processing_pipeline
from interview_intelligence.config.settings import Settings
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)
from interview_intelligence.pipeline.models import InterviewProcessingRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the persisted Interview Intelligence processing workflow."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--company", required=True)
    parser.add_argument("--person", required=True)
    parser.add_argument("--interview-datetime", required=True)
    parser.add_argument("--sequence", type=int, default=1)
    parser.add_argument("--role")
    parser.add_argument("--target-level")
    parser.add_argument("--num-speakers", type=int, default=2)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()

    settings = Settings()
    settings.ensure_directories()

    output_root = args.output_root or settings.recordings_dir
    database_path = args.database or settings.database_path

    database = SQLiteDatabase(database_path)
    database.initialize()

    events = []

    def collect_event(event):
        events.append(event)
        print(
            json.dumps(
                {
                    "job_id": str(event.job_id),
                    "stage": event.stage.value,
                    "status": event.status.value,
                    "progress_percent": event.progress_percent,
                    "message": event.message,
                }
            ),
            flush=True,
        )

    coordinator = InterviewProcessingCoordinator(
        pipeline=build_local_processing_pipeline(output_root),
        interview_repository=InterviewRepository(database),
        job_service=ProcessingJobService(
            ProcessingJobRepository(database),
            listener=collect_event,
        ),
    )

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

    job_id, result = coordinator.run(request)

    print(
        json.dumps(
            {
                "job_id": str(job_id),
                "artifact_root": str(result.artifacts.root_dir),
                "segment_count": len(result.segments),
                "quality_issue_count": len(result.quality_issues),
                "speaker_mapping_confidence": result.speaker_mapping_confidence,
                "event_count": len(events),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
