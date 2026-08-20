import json
import shutil
from pathlib import Path

from interview_intelligence.pipeline.models import (
    InterviewArtifactPaths,
    InterviewProcessingRequest,
    ProcessedTranscriptSegment,
)
from interview_intelligence.quality.models import QualityIssue


class InterviewArtifactExporter:
    """Write stable production artifacts for UI, persistence, and cloud sync."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.expanduser().resolve()

    def build_paths(
        self,
        request: InterviewProcessingRequest,
    ) -> InterviewArtifactPaths:
        timestamp = request.interview_datetime.strftime("%Y%m%d_%H%M")
        safe_company = self._slug(request.company)
        safe_person = self._slug(request.recruiter_or_interviewer)
        suffix = f"{request.sequence_number:02d}"

        root = self.base_dir / safe_company / f"{timestamp}_{safe_person}_{suffix}"
        original_audio = root / f"original{request.source_audio.suffix.lower()}"

        return InterviewArtifactPaths(
            root_dir=root,
            original_audio=original_audio,
            transcript_text=root / "transcript.txt",
            transcript_json=root / "transcript.json",
            metadata_json=root / "metadata.json",
            quality_json=root / "quality.json",
        )

    def export(
        self,
        request: InterviewProcessingRequest,
        paths: InterviewArtifactPaths,
        segments: list[ProcessedTranscriptSegment],
        quality_issues: list[QualityIssue],
        metadata: dict[str, object],
    ) -> None:
        paths.root_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(request.source_audio, paths.original_audio)

        transcript_lines = []
        for segment in segments:
            quality_marker = (
                f" [QUALITY:{','.join(segment.quality_flags)}]"
                if segment.quality_flags
                else ""
            )
            transcript_lines.append(
                f"[{self._format_timestamp(segment.start_seconds)} -> "
                f"{self._format_timestamp(segment.end_seconds)}] "
                f"{segment.speaker_role or segment.speaker_id or 'UNKNOWN'}"
                f"{quality_marker}: {segment.text}"
            )

        paths.transcript_text.write_text(
            "\n".join(transcript_lines) + "\n",
            encoding="utf-8",
        )

        paths.transcript_json.write_text(
            json.dumps(
                [segment.model_dump(mode="json") for segment in segments],
                indent=2,
            ),
            encoding="utf-8",
        )

        paths.quality_json.write_text(
            json.dumps(
                [issue.model_dump(mode="json") for issue in quality_issues],
                indent=2,
            ),
            encoding="utf-8",
        )

        paths.metadata_json.write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = "".join(
            char if char.isalnum() else "_"
            for char in value.strip()
        )
        return "_".join(part for part in cleaned.split("_") if part)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
