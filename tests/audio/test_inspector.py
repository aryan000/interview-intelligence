import json
import subprocess
from pathlib import Path

import pytest

from interview_intelligence.audio.errors import AudioInspectionError
from interview_intelligence.audio.inspector import FFprobeAudioInspector


def test_inspector_parses_ffprobe_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "call.m4a"
    audio.write_bytes(b"fake-audio")

    payload = {
        "streams": [
            {
                "index": 0,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
                "bit_rate": "128000",
            }
        ],
        "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "5234.10",
            "bit_rate": "130000",
            "size": "1000",
        },
    }

    monkeypatch.setattr("shutil.which", lambda _: "/opt/homebrew/bin/ffprobe")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        ),
    )

    metadata = FFprobeAudioInspector().inspect(audio)

    assert metadata.codec == "aac"
    assert metadata.duration_seconds == 5234.10
    assert metadata.sample_rate == 48000
    assert metadata.channels == 2
    assert metadata.bit_rate == 128000
    assert metadata.file_size_bytes == 1000


def test_inspector_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AudioInspectionError, match="does not exist"):
        FFprobeAudioInspector().inspect(tmp_path / "missing.wav")
