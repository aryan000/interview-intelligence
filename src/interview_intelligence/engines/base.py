from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from interview_intelligence.domain.models import TranscriptSegment


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_path: Path
    language: str | None = None
    initial_prompt: str | None = None
    word_timestamps: bool = False


@dataclass(frozen=True)
class TranscriptionResult:
    language: str | None
    text: str
    segments: list[TranscriptSegment]
    engine_name: str
    model_name: str


ProgressCallback = Callable[[float, float], None]


class TranscriptionEngine(ABC):
    @abstractmethod
    def transcribe(
        self,
        request: TranscriptionRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file and preserve the original timeline."""


class DiarizationEngine(ABC):
    @abstractmethod
    def diarize(self, audio_path: Path) -> list[tuple[float, float, str]]:
        """Return speaker turns as (start_seconds, end_seconds, speaker_id)."""
