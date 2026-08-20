from interview_intelligence.diarization.aligner import SpeakerAligner
from interview_intelligence.diarization.models import SpeakerTurn
from interview_intelligence.domain.models import TranscriptSegment


def test_alignment_matches_interview_handoff_pattern() -> None:
    segments = [
        TranscriptSegment(
            sequence_number=0,
            start_seconds=24.4,
            end_seconds=27.7,
            text="Maybe a quick intro about yourself.",
        ),
        TranscriptSegment(
            sequence_number=1,
            start_seconds=27.7,
            end_seconds=32.2,
            text="Okay sure. So hey, I am Arun.",
        ),
        TranscriptSegment(
            sequence_number=2,
            start_seconds=56.6,
            end_seconds=56.9,
            text="Okay.",
        ),
    ]

    turns = [
        SpeakerTurn(
            start_seconds=18.5,
            end_seconds=28.04,
            speaker_id="SPEAKER_00",
        ),
        SpeakerTurn(
            start_seconds=28.33,
            end_seconds=56.66,
            speaker_id="SPEAKER_01",
        ),
        SpeakerTurn(
            start_seconds=56.66,
            end_seconds=57.0,
            speaker_id="SPEAKER_00",
        ),
    ]

    aligned = SpeakerAligner().align(segments, turns)

    assert aligned[0].speaker_id == "SPEAKER_00"
    assert aligned[1].speaker_id == "SPEAKER_01"
    assert aligned[2].speaker_id == "SPEAKER_00"
