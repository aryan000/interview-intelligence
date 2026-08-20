from datetime import datetime
from pathlib import Path

from interview_intelligence.pipeline.exporter import InterviewArtifactExporter
from interview_intelligence.pipeline.models import InterviewProcessingRequest


def test_exporter_builds_expected_interview_folder(tmp_path: Path) -> None:
    request = InterviewProcessingRequest(
        source_audio=Path("/tmp/call.mp3"),
        company="PhonePe",
        recruiter_or_interviewer="Tushar",
        sequence_number=2,
        interview_datetime=datetime(2026, 7, 30, 12, 0),
    )

    paths = InterviewArtifactExporter(tmp_path).build_paths(request)

    assert paths.root_dir == tmp_path / "PhonePe" / "20260730_1200_Tushar_02"
    assert paths.original_audio.name == "original.mp3"
