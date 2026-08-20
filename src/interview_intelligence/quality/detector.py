import re
from collections import Counter

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.quality.models import QualityFlag, QualityIssue


class TranscriptQualityDetector:
    """Detect obviously suspicious transcript output without rewriting it."""

    def __init__(
        self,
        repetition_threshold: int = 8,
        minimum_words_for_zero_duration_flag: int = 4,
    ) -> None:
        self.repetition_threshold = repetition_threshold
        self.minimum_words_for_zero_duration_flag = minimum_words_for_zero_duration_flag

    def detect(self, segments: list[TranscriptSegment]) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        for index, segment in enumerate(segments):
            issues.extend(self._detect_repetition(index, segment))
            issues.extend(self._detect_zero_duration(index, segment))
            issues.extend(self._detect_suspicious_tokens(index, segment))

        return issues

    def _detect_repetition(
        self,
        index: int,
        segment: TranscriptSegment,
    ) -> list[QualityIssue]:
        normalized_words = re.findall(r"[a-zA-Z]+", segment.text.lower())
        if not normalized_words:
            return []

        counts = Counter(normalized_words)
        word, count = counts.most_common(1)[0]

        if count < self.repetition_threshold:
            return []

        ratio = count / len(normalized_words)
        if ratio < 0.6:
            return []

        return [
            QualityIssue(
                flag=QualityFlag.REPETITION_LOOP,
                segment_index=index,
                message=(
                    f"Word {word!r} repeats {count} times "
                    f"({ratio:.0%} of segment words)."
                ),
                severity="high",
            )
        ]

    def _detect_zero_duration(
        self,
        index: int,
        segment: TranscriptSegment,
    ) -> list[QualityIssue]:
        duration = segment.end_seconds - segment.start_seconds
        word_count = len(segment.text.split())

        if duration > 0.05 or word_count < self.minimum_words_for_zero_duration_flag:
            return []

        return [
            QualityIssue(
                flag=QualityFlag.ZERO_DURATION_TEXT,
                segment_index=index,
                message=(
                    f"{word_count} words mapped to only {duration:.3f}s of audio."
                ),
                severity="high",
            )
        ]

    def _detect_suspicious_tokens(
        self,
        index: int,
        segment: TranscriptSegment,
    ) -> list[QualityIssue]:
        suspicious = ("сотруд", "사건")
        lowered = segment.text.lower()

        for token in suspicious:
            if token in lowered:
                return [
                    QualityIssue(
                        flag=QualityFlag.SUSPICIOUS_TOKEN,
                        segment_index=index,
                        message=f"Unexpected token detected: {token!r}.",
                        severity="medium",
                    )
                ]

        return []
