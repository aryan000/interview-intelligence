import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from interview_intelligence.audio.errors import AudioInspectionError, FFprobeNotFoundError
from interview_intelligence.audio.models import AudioMetadata


class AudioInspector(ABC):
    @abstractmethod
    def inspect(self, audio_path: Path) -> AudioMetadata:
        """Inspect an audio recording without converting it."""


class FFprobeAudioInspector(AudioInspector):
    """Read audio metadata using the ffprobe executable."""

    def __init__(self, executable: str = "ffprobe") -> None:
        self.executable = executable

    def inspect(self, audio_path: Path) -> AudioMetadata:
        path = audio_path.expanduser().resolve()

        if not path.is_file():
            raise AudioInspectionError(f"Audio file does not exist: {path}")

        executable_path = shutil.which(self.executable)
        if executable_path is None:
            raise FFprobeNotFoundError(
                f"{self.executable!r} was not found on PATH. Install FFmpeg first."
            )

        command = [
            executable_path,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration,bit_rate,size:"
            "stream=index,codec_type,codec_name,sample_rate,channels,bit_rate",
            "-of",
            "json",
            str(path),
        ]

        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or "unknown ffprobe error"
            raise AudioInspectionError(f"ffprobe failed for {path}: {detail}") from exc

        try:
            payload: dict[str, Any] = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AudioInspectionError("ffprobe returned invalid JSON") from exc

        streams = payload.get("streams", [])
        audio_stream = next(
            (stream for stream in streams if stream.get("codec_type") == "audio"),
            None,
        )
        if audio_stream is None:
            raise AudioInspectionError(f"No audio stream found in: {path}")

        format_data = payload.get("format", {})

        codec = audio_stream.get("codec_name")
        sample_rate = self._to_int(audio_stream.get("sample_rate"))
        channels = self._to_int(audio_stream.get("channels"))
        duration = self._to_float(format_data.get("duration"))

        if not codec or sample_rate is None or channels is None or duration is None:
            raise AudioInspectionError(f"Incomplete audio metadata returned for: {path}")

        bit_rate = self._to_int(audio_stream.get("bit_rate")) or self._to_int(
            format_data.get("bit_rate")
        )
        reported_size = self._to_int(format_data.get("size"))

        return AudioMetadata(
            path=path,
            container=format_data.get("format_name"),
            codec=codec,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            bit_rate=bit_rate,
            file_size_bytes=reported_size if reported_size is not None else path.stat().st_size,
        )

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value in (None, "", "N/A"):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, "", "N/A"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
