import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from interview_intelligence.audio.errors import AudioPreparationError
from interview_intelligence.audio.inspector import AudioInspector
from interview_intelligence.audio.models import AudioMetadata


@dataclass(frozen=True)
class AudioPreparationResult:
    source: AudioMetadata
    prepared: AudioMetadata
    output_path: Path
    elapsed_seconds: float
    warnings: tuple[str, ...]


class AudioPreparer(ABC):
    @abstractmethod
    def prepare(self, source_path: Path, output_path: Path) -> AudioPreparationResult:
        """Prepare an audio file for deterministic downstream processing."""


class FFmpegAudioPreparer(AudioPreparer):
    """Normalize input audio to 16 kHz mono PCM WAV using FFmpeg."""

    def __init__(
        self,
        inspector: AudioInspector,
        executable: str = "ffmpeg",
    ) -> None:
        self.inspector = inspector
        self.executable = executable

    def prepare(self, source_path: Path, output_path: Path) -> AudioPreparationResult:
        source = self.inspector.inspect(source_path)
        output = output_path.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        command = [
            self.executable,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            str(source.path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-y",
            str(output),
        ]

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise AudioPreparationError(
                f"{self.executable!r} was not found on PATH. Install FFmpeg first."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or "unknown FFmpeg error"
            raise AudioPreparationError(
                f"FFmpeg failed to prepare {source.path}: {detail}"
            ) from exc

        elapsed = time.perf_counter() - started

        if not output.is_file():
            raise AudioPreparationError(
                f"FFmpeg completed but did not create output: {output}"
            )

        prepared = self.inspector.inspect(output)
        self._validate_prepared_audio(prepared)

        warnings = tuple(
            line.strip()
            for line in completed.stderr.splitlines()
            if line.strip()
        )

        return AudioPreparationResult(
            source=source,
            prepared=prepared,
            output_path=output,
            elapsed_seconds=elapsed,
            warnings=warnings,
        )

    @staticmethod
    def _validate_prepared_audio(metadata: AudioMetadata) -> None:
        if metadata.codec != "pcm_s16le":
            raise AudioPreparationError(
                f"Expected pcm_s16le output, got {metadata.codec}"
            )
        if metadata.sample_rate != 16000:
            raise AudioPreparationError(
                f"Expected 16000 Hz output, got {metadata.sample_rate}"
            )
        if metadata.channels != 1:
            raise AudioPreparationError(
                f"Expected mono output, got {metadata.channels} channels"
            )
