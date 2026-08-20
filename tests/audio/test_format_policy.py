from pathlib import Path

from interview_intelligence.audio.format_policy import AudioFormatPolicy
from interview_intelligence.audio.models import AudioMetadata


def test_valid_audio_is_not_eagerly_converted() -> None:
    metadata = AudioMetadata(
        path=Path("interview.aac"),
        container="aac",
        codec="aac",
        duration_seconds=5400,
        sample_rate=48000,
        channels=2,
        file_size_bytes=1_000_000,
    )

    decision = AudioFormatPolicy().decide(metadata)

    assert decision.requires_normalization is False
    assert "defer conversion" in decision.reason
