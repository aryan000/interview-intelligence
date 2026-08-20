from dataclasses import dataclass

from interview_intelligence.audio.models import AudioMetadata


@dataclass(frozen=True)
class AudioPreparationDecision:
    requires_normalization: bool
    reason: str


class AudioFormatPolicy:
    """Decide whether an input should be normalized before transcription.

    This policy deliberately does not perform conversion. The transcription engine
    remains the source of truth for what it can decode directly. V1 starts with a
    conservative policy and will refine it using real MLX/Whisper benchmarks.
    """

    def decide(self, metadata: AudioMetadata) -> AudioPreparationDecision:
        if metadata.sample_rate <= 0 or metadata.channels <= 0:
            return AudioPreparationDecision(True, "invalid audio stream metadata")

        return AudioPreparationDecision(
            False,
            "valid audio stream detected; defer conversion until the engine requires it",
        )
