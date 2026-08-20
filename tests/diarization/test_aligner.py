from interview_intelligence.diarization.aligner import SpeakerAligner
from interview_intelligence.diarization.models import SpeakerTurn
from interview_intelligence.domain.models import TranscriptSegment


def test_aligner_uses_maximum_overlap() -> None:
    segment = TranscriptSegment(
        sequence_number=0,
        start_seconds=10,
        end_seconds=15,
        text="I would use Kafka.",
    )
    turns = [
        SpeakerTurn(start_seconds=9, end_seconds=11, speaker_id="SPEAKER_00"),
        SpeakerTurn(start_seconds=11, end_seconds=16, speaker_id="SPEAKER_01"),
    ]

    result = SpeakerAligner().align([segment], turns)

    assert result[0].speaker_id == "SPEAKER_01"


def test_aligner_leaves_uncovered_segment_unknown() -> None:
    segment = TranscriptSegment(
        sequence_number=0,
        start_seconds=20,
        end_seconds=25,
        text="hello",
    )

    result = SpeakerAligner().align(
        [segment],
        [SpeakerTurn(start_seconds=0, end_seconds=5, speaker_id="SPEAKER_00")],
    )

    assert result[0].speaker_id is None
