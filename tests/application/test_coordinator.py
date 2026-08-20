from datetime import UTC, datetime
from pathlib import Path

import pytest

from interview_intelligence.application.coordinator import (
    InterviewProcessingCoordinator,
)
from interview_intelligence.audio.models import AudioMetadata
from interview_intelligence.domain.enums import JobStatus
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.database import SQLiteDatabase
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
    def __init__(self, output_dir: Path, should_fail: bool = False) -> None:
        self.inspector = StubInspector()
        self.output_dir = output_dir
        self.should_fail = should_fail

    def process(
        self,
        request: InterviewProcessingRequest,
    ) -> InterviewProcessingResult:
        if self.should_fail:
            raise RuntimeError("boom")

        root = self.output_dir / "PhonePe" / "sample"
        root.mkdir(parents=True, exist_ok=True)

        metadata = self.inspector.inspect(request.source_audio)

        return InterviewProcessingResult(
            source_metadata=metadata,
            prepared_metadata=metadata,
            segments=[],
            quality_issues=[],
            candidate_speaker_id="SPEAKER_01",
            interviewer_speaker_id="SPEAKER_00",
            speaker_mapping_confidence=0.9,
            artifacts=InterviewArtifactPaths(
                root_dir=root,
                original_audio=root / "original.wav",
                transcript_text=root / "transcript.txt",
                transcript_json=root / "transcript.json",
                metadata_json=root / "metadata.json",
                quality_json=root / "quality.json",
            ),
            transcription_seconds=10,
            diarization_seconds=2,
            total_seconds=12,
        )


def build_coordinator(
    tmp_path: Path,
    should_fail: bool = False,
) -> tuple[
    InterviewProcessingCoordinator,
    InterviewRepository,
    ProcessingJobRepository,
]:
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()

    interviews = InterviewRepository(database)
    jobs = ProcessingJobRepository(database)

    coordinator = InterviewProcessingCoordinator(
        pipeline=StubPipeline(tmp_path / "output", should_fail),  # type: ignore[arg-type]
        interview_repository=interviews,
        job_service=ProcessingJobService(jobs),
    )

    return coordinator, interviews, jobs


def test_coordinator_persists_successful_job(tmp_path: Path) -> None:
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")

    coordinator, interviews, jobs = build_coordinator(tmp_path)

    job_id, result = coordinator.run(
        InterviewProcessingRequest(
            source_audio=source,
            company="PhonePe",
            recruiter_or_interviewer="Tushar",
            interview_datetime=datetime.now(UTC),
        )
    )

    job = jobs.get(job_id)
    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.progress_percent == 100

    interview = interviews.get(job.interview_id)
    assert interview is not None
    assert interview.artifact_root_path == str(result.artifacts.root_dir)


def test_coordinator_persists_failed_job(tmp_path: Path) -> None:
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")

    coordinator, _, jobs = build_coordinator(
        tmp_path,
        should_fail=True,
    )

    with pytest.raises(RuntimeError, match="boom"):
        coordinator.run(
            InterviewProcessingRequest(
                source_audio=source,
                company="PhonePe",
                recruiter_or_interviewer="Tushar",
                interview_datetime=datetime.now(UTC),
            )
        )

    with jobs.database.connect() as connection:
        row = connection.execute(
            "SELECT status, error_message FROM processing_jobs LIMIT 1"
        ).fetchone()

    assert row is not None
    assert row["status"] == JobStatus.FAILED.value
    assert row["error_message"] == "boom"
