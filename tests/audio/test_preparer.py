import subprocess
from pathlib import Path

import pytest

from interview_intelligence.audio.errors import AudioPreparationError
from interview_intelligence.audio.models import AudioMetadata
from interview_intelligence.audio.preparer import FFmpegAudioPreparer


class StubInspector:
    def inspect(self, audio_path: Path) -> AudioMetadata:
        path = audio_path.expanduser().resolve()
        if path.suffix == ".wav":
            return AudioMetadata(
                path=path,
                container="wav",
                codec="pcm_s16le",
                duration_seconds=60.0,
                sample_rate=16000,
                channels=1,
                file_size_bytes=1000,
            )
        return AudioMetadata(
            path=path,
            container="mp3",
            codec="mp3",
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=2000,
        )


def test_preparer_normalizes_to_canonical_wav(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "interview.mp3"
    source.write_bytes(b"source")
    output = tmp_path / "prepared.wav"

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"prepared")
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="[mp3float] Header missing\n",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result = FFmpegAudioPreparer(StubInspector()).prepare(source, output)

    assert result.output_path == output.resolve()
    assert result.prepared.codec == "pcm_s16le"
    assert result.prepared.sample_rate == 16000
    assert result.prepared.channels == 1
    assert result.warnings == ("[mp3float] Header missing",)
    assert result.elapsed_seconds >= 0


def test_preparer_raises_when_ffmpeg_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "interview.mp3"
    source.write_bytes(b"source")
    output = tmp_path / "prepared.wav"

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd="ffmpeg",
            stderr="decode failed",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(AudioPreparationError, match="decode failed"):
        FFmpegAudioPreparer(StubInspector()).prepare(source, output)
