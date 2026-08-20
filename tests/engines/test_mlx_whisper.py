from pathlib import Path
from types import SimpleNamespace

import pytest

from interview_intelligence.engines.base import TranscriptionRequest
from interview_intelligence.engines.mlx_whisper import MLXWhisperEngine


def test_mlx_engine_maps_segments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_module = SimpleNamespace(
        transcribe=lambda *args, **kwargs: {
            "language": "en",
            "text": "Hello world.",
            "segments": [
                {
                    "start": 1.0,
                    "end": 2.5,
                    "text": " Hello world. ",
                }
            ],
        }
    )

    monkeypatch.setattr(
        "interview_intelligence.engines.mlx_whisper.import_module",
        lambda _: fake_module,
    )

    result = MLXWhisperEngine().transcribe(
        TranscriptionRequest(audio_path=audio)
    )

    assert result.language == "en"
    assert result.text == "Hello world."
    assert result.engine_name == "mlx-whisper"
    assert len(result.segments) == 1
    assert result.segments[0].start_seconds == 1.0
    assert result.segments[0].end_seconds == 2.5
    assert result.segments[0].text == "Hello world."


def test_mlx_engine_clamps_reversed_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_module = SimpleNamespace(
        transcribe=lambda *args, **kwargs: {
            "language": "en",
            "text": "NetNet the strategy was.",
            "segments": [
                {
                    "start": 42.5,
                    "end": 42.48,
                    "text": "NetNet the strategy was.",
                }
            ],
        }
    )

    monkeypatch.setattr(
        "interview_intelligence.engines.mlx_whisper.import_module",
        lambda _: fake_module,
    )

    result = MLXWhisperEngine().transcribe(
        TranscriptionRequest(audio_path=audio)
    )

    assert len(result.segments) == 1
    assert result.segments[0].start_seconds == 42.5
    assert result.segments[0].end_seconds == 42.5


def test_mlx_engine_rejects_missing_audio(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MLXWhisperEngine().transcribe(
            TranscriptionRequest(audio_path=tmp_path / "missing.wav")
        )
