from collections.abc import Callable
from importlib import import_module
from typing import Any, cast

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import (
    ProgressCallback,
    TranscriptionEngine,
    TranscriptionRequest,
    TranscriptionResult,
)


class MLXWhisperEngine(TranscriptionEngine):
    """High-quality local transcription backed by mlx-whisper."""

    def __init__(
        self,
        model_repo: str = "mlx-community/whisper-large-v3-mlx",
    ) -> None:
        self.model_repo = model_repo

    def transcribe(
        self,
        request: TranscriptionRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        if not request.audio_path.is_file():
            raise FileNotFoundError(request.audio_path)

        mlx_whisper = import_module("mlx_whisper")
        transcribe_fn = cast(
            Callable[..., dict[str, Any]],
            mlx_whisper.transcribe,
        )

        raw = transcribe_fn(
            str(request.audio_path),
            path_or_hf_repo=self.model_repo,
            language=request.language,
            initial_prompt=request.initial_prompt,
            word_timestamps=request.word_timestamps,
            verbose=None,
        )

        raw_segments = raw.get("segments", [])
        segments: list[TranscriptSegment] = []

        for index, segment in enumerate(raw_segments):
            if not isinstance(segment, dict):
                continue

            start = self._to_float(segment.get("start"))
            end = self._to_float(segment.get("end"))
            text = str(segment.get("text", "")).strip()

            if start is None or end is None or not text:
                continue

            # Whisper can occasionally emit a malformed timestamp pair where
            # end < start. Do not crash a long-running transcription job.
            # Preserve the text at a zero-duration point so downstream quality
            # checks can flag the segment for review/re-transcription.
            if end < start:
                end = start

            segments.append(
                TranscriptSegment(
                    sequence_number=index,
                    start_seconds=start,
                    end_seconds=end,
                    text=text,
                )
            )

            if progress_callback is not None:
                progress_callback(end, end)

        return TranscriptionResult(
            language=self._to_optional_str(raw.get("language")),
            text=str(raw.get("text", "")).strip(),
            segments=segments,
            engine_name="mlx-whisper",
            model_name=self.model_repo,
        )

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)
