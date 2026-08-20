from datetime import datetime
from pathlib import Path

from interview_intelligence.audio.models import AudioMetadata
from interview_intelligence.audio.preparer import AudioPreparationResult
from interview_intelligence.diarization.models import (
    DiarizationResult,
    SpeakerTurn,
)
from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import (
    TranscriptionEngine,
    TranscriptionRequest,
    TranscriptionResult,
)
from interview_intelligence.pipeline.exporter import InterviewArtifactExporter
from interview_intelligence.pipeline.models import InterviewProcessingRequest
from interview_intelligence.pipeline.processor import InterviewProcessingPipeline


class StubInspector:
    def inspect(self, audio_path: Path) -> AudioMetadata:
        return AudioMetadata(
            path=audio_path.resolve(),
            container="wav",
            codec="pcm_s16le",
            duration_seconds=60,
            sample_rate=16000,
            channels=1,
            file_size_bytes=100,
        )


class StubPreparer:
    def prepare(self, source_path: Path, output_path: Path) -> AudioPreparationResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"prepared")
        metadata = StubInspector().inspect(output_path)
        return AudioPreparationResult(
            source=StubInspector().inspect(source_path),
            prepared=metadata,
            output_path=output_path,
            elapsed_seconds=0.01,
            warnings=(),
        )


class StubTranscriptionEngine(TranscriptionEngine):
    def transcribe(
        self,
        request: TranscriptionRequest,
        progress_callback=None,
    ) -> TranscriptionResult:
        return TranscriptionResult(
            language="en",
            text="I'll explain the process. I've been working with Amazon.",
            segments=[
                TranscriptSegment(
                    sequence_number=0,
                    start_seconds=0,
                    end_seconds=10,
                    text="I'll explain the process.",
                ),
                TranscriptSegment(
                    sequence_number=1,
                    start_seconds=12,
                    end_seconds=20,
                    text="I've been working with Amazon.",
                ),
            ],
            engine_name="stub",
            model_name="stub",
        )


class StubDiarizationEngine:
    def diarize(self, audio_path: Path, num_speakers: int | None = 2) -> DiarizationResult:
        return DiarizationResult(
            turns=[
                SpeakerTurn(
                    start_seconds=0,
                    end_seconds=10,
                    speaker_id="SPEAKER_00",
                ),
                SpeakerTurn(
                    start_seconds=12,
                    end_seconds=20,
                    speaker_id="SPEAKER_01",
                ),
            ],
            speaker_count=2,
            engine_name="stub-diarization",
            model_name="stub",
        )


def test_pipeline_exports_processed_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")

    pipeline = InterviewProcessingPipeline(
        inspector=StubInspector(),
        preparer=StubPreparer(),
        transcription_engine=StubTranscriptionEngine(),
        diarization_engine=StubDiarizationEngine(),  # type: ignore[arg-type]
        exporter=InterviewArtifactExporter(tmp_path / "output"),
    )

    result = pipeline.process(
        InterviewProcessingRequest(
            source_audio=source,
            company="PhonePe",
            recruiter_or_interviewer="Tushar",
            interview_datetime=datetime(2026, 7, 30, 12, 0),
        )
    )

    assert result.artifacts.transcript_text.is_file()
    assert result.artifacts.transcript_json.is_file()
    assert result.artifacts.metadata_json.is_file()
    assert result.artifacts.quality_json.is_file()
    assert len(result.segments) == 2
