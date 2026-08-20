from pathlib import Path

from interview_intelligence.audio.models import AudioMetadata


def test_audio_metadata_reports_mono() -> None:
    metadata = AudioMetadata(
        path=Path("sample.wav"),
        container="wav",
        codec="pcm_s16le",
        duration_seconds=10.0,
        sample_rate=16000,
        channels=1,
        file_size_bytes=100,
    )

    assert metadata.is_mono is True
