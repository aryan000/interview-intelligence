from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.transcription.sanitizer import TranscriptTimelineSanitizer


def make_segment(seq: int, start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        sequence_number=seq,
        start_seconds=start,
        end_seconds=end,
        text=text,
    )


def test_drops_segments_starting_beyond_audio_duration() -> None:
    result = TranscriptTimelineSanitizer().sanitize(
        [
            make_segment(0, 118.0, 119.0, "valid"),
            make_segment(1, 121.0, 122.0, "hallucinated beyond end"),
        ],
        audio_duration_seconds=120.0,
    )

    assert [segment.text for segment in result.segments] == ["valid"]
    assert result.dropped_out_of_bounds == 1


def test_clamps_segment_crossing_audio_end() -> None:
    result = TranscriptTimelineSanitizer().sanitize(
        [make_segment(0, 119.5, 120.8, "crosses end")],
        audio_duration_seconds=120.0,
    )

    assert result.segments[0].end_seconds == 120.0
    assert result.clamped_segments == 1
