from interview_intelligence.diarization.models import SpeakerTurn
from interview_intelligence.domain.models import TranscriptSegment


class SpeakerAligner:
    """Assign each transcript segment to the speaker with maximum time overlap."""

    def align(
        self,
        segments: list[TranscriptSegment],
        turns: list[SpeakerTurn],
    ) -> list[TranscriptSegment]:
        aligned: list[TranscriptSegment] = []

        for segment in segments:
            speaker_id = self._best_speaker(segment, turns)
            aligned.append(
                TranscriptSegment(
                    sequence_number=segment.sequence_number,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    speaker_id=speaker_id,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )

        return aligned

    @staticmethod
    def _best_speaker(
        segment: TranscriptSegment,
        turns: list[SpeakerTurn],
    ) -> str | None:
        overlap_by_speaker: dict[str, float] = {}

        for turn in turns:
            overlap = max(
                0.0,
                min(segment.end_seconds, turn.end_seconds)
                - max(segment.start_seconds, turn.start_seconds),
            )
            if overlap <= 0:
                continue

            overlap_by_speaker[turn.speaker_id] = (
                overlap_by_speaker.get(turn.speaker_id, 0.0) + overlap
            )

        if not overlap_by_speaker:
            return None

        return max(
            overlap_by_speaker,
            key=lambda speaker_id: overlap_by_speaker[speaker_id],
        )
