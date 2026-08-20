import os
from pathlib import Path

from interview_intelligence.audio.inspector import FFprobeAudioInspector
from interview_intelligence.audio.preparer import FFmpegAudioPreparer
from interview_intelligence.diarization.pyannote_engine import (
    PyannoteDiarizationEngine,
)
from interview_intelligence.engines.mlx_whisper import MLXWhisperEngine
from interview_intelligence.pipeline.exporter import InterviewArtifactExporter
from interview_intelligence.pipeline.processor import InterviewProcessingPipeline


def build_local_processing_pipeline(
    output_root: Path,
) -> InterviewProcessingPipeline:
    inspector = FFprobeAudioInspector()

    return InterviewProcessingPipeline(
        inspector=inspector,
        preparer=FFmpegAudioPreparer(inspector),
        transcription_engine=MLXWhisperEngine(),
        diarization_engine=PyannoteDiarizationEngine(
            token=os.getenv("HF_TOKEN"),
        ),
        exporter=InterviewArtifactExporter(output_root),
    )
