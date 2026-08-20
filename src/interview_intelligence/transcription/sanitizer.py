from dataclasses import dataclass

from interview_intelligence.domain.models import TranscriptSegment


@dataclass(frozen=True)
class SanitizationResult:
    segments: list[TranscriptSegment]
    dropped_out_of_bounds: int
    clamped_segments: int


class TranscriptTimelineSanitizer:
    """Keep transcript timestamps inside the authoritative audio timeline."""

    def sanitize(
        self,
        segments: list[TranscriptSegment],
        audio_duration_seconds: float,
        tolerance_seconds: float = 0.25,
    ) -> SanitizationResult:
        sanitized: list[TranscriptSegment] = []
        dropped = 0
        clamped = 0

        for segment in segments:
            if segment.start_seconds > audio_duration_seconds + tolerance_seconds:
                dropped += 1
                continue

            start = min(segment.start_seconds, audio_duration_seconds)
            end = min(segment.end_seconds, audio_duration_seconds)

            if end < start:
                end = start

            if (
                start != segment.start_seconds
                or end != segment.end_seconds
            ):
                clamped += 1

            sanitized.append(
                TranscriptSegment(
                    sequence_number=len(sanitized),
                    start_seconds=start,
                    end_seconds=end,
                    speaker_id=segment.speaker_id,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )

        return SanitizationResult(
            segments=sanitized,
            dropped_out_of_bounds=dropped,
            clamped_segments=clamped,
        )
