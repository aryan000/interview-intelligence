from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.quality.detector import TranscriptQualityDetector
from interview_intelligence.quality.models import QualityFlag


def make_segment(text: str, start: float = 0.0, end: float = 5.0) -> TranscriptSegment:
    return TranscriptSegment(
        sequence_number=0,
        start_seconds=start,
        end_seconds=end,
        text=text,
    )


def test_detects_repetition_loop() -> None:
    issues = TranscriptQualityDetector().detect(
        [make_segment("non non non non non non non non non non")]
    )

    assert len(issues) == 1
    assert issues[0].flag == QualityFlag.REPETITION_LOOP


def test_detects_zero_duration_with_many_words() -> None:
    issues = TranscriptQualityDetector().detect(
        [make_segment("this should not fit in zero time", start=10.0, end=10.0)]
    )

    assert any(issue.flag == QualityFlag.ZERO_DURATION_TEXT for issue in issues)


def test_clean_segment_has_no_issue() -> None:
    issues = TranscriptQualityDetector().detect(
        [make_segment("We used Kafka and an outbox pattern for reliable delivery.")]
    )

    assert issues == []
