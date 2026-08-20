from datetime import UTC, datetime
from pathlib import Path

from interview_intelligence.application.existing_interview_coordinator import (
    ExistingInterviewProcessingCoordinator,
)
from interview_intelligence.audio.models import AudioMetadata
from interview_intelligence.domain.enums import JobStatus
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.models import InterviewRecord
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)
from interview_intelligence.pipeline.models import (
    InterviewArtifactPaths,
    InterviewProcessingRequest,
    InterviewProcessingResult,
)


class StubInspector:
    def inspect(self, audio_path: Path) -> AudioMetadata:
        return AudioMetadata(
            path=audio_path.resolve(),
            container="wav",
            codec="pcm_s16le",
            duration_seconds=120,
            sample_rate=16000,
            channels=1,
            file_size_bytes=100,
        )


class StubPipeline:
    def __init__(self, output_dir: Path) -> None:
        self.inspector = StubInspector()
        self.output_dir = output_dir

    def process(
        self,
        request: InterviewProcessingRequest,
    ) -> InterviewProcessingResult:
        root = self.output_dir / "result"
        root.mkdir(parents=True, exist_ok=True)
        metadata = self.inspector.inspect(request.source_audio)

        return InterviewProcessingResult(
            source_metadata=metadata,
            prepared_metadata=metadata,
            segments=[],
            quality_issues=[],
            candidate_speaker_id="SPEAKER_01",
            interviewer_speaker_id="SPEAKER_00",
            speaker_mapping_confidence=0.8,
            artifacts=InterviewArtifactPaths(
                root_dir=root,
                original_audio=root / "original.wav",
                transcript_text=root / "transcript.txt",
                transcript_json=root / "transcript.json",
                metadata_json=root / "metadata.json",
                quality_json=root / "quality.json",
            ),
            transcription_seconds=1,
            diarization_seconds=1,
            total_seconds=2,
        )


def test_existing_interview_is_processed_without_duplicate_row(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()

    interviews = InterviewRepository(database)
    jobs = ProcessingJobRepository(database)

    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")

    now = datetime.now(UTC)
    interview = InterviewRecord(
        company="PhonePe",
        recruiter_or_interviewer="Tushar",
        interview_datetime=now,
        sequence_number=1,
        source_audio_path=str(source),
        created_at=now,
        updated_at=now,
    )
    interviews.save(interview)

    service = ProcessingJobService(jobs)
    job = service.create(interview.id, total_audio_seconds=120)

    coordinator = ExistingInterviewProcessingCoordinator(
        pipeline=StubPipeline(tmp_path / "output"),  # type: ignore[arg-type]
        interview_repository=interviews,
        job_service=service,
    )

    coordinator.run(interview.id, job.id)

    with database.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM interviews"
        ).fetchone()["count"]

    loaded_job = jobs.get(job.id)

    assert count == 1
    assert loaded_job is not None
    assert loaded_job.status == JobStatus.COMPLETED
