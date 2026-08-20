from interview_intelligence.diarization.roles import SpeakerRoleMapper
from interview_intelligence.domain.models import TranscriptSegment


def segment(
    seq: int,
    start: float,
    speaker: str,
    text: str,
) -> TranscriptSegment:
    return TranscriptSegment(
        sequence_number=seq,
        start_seconds=start,
        end_seconds=start + 3,
        speaker_id=speaker,
        text=text,
    )


def test_maps_interviewer_and_candidate_from_intro_semantics() -> None:
    segments = [
        segment(
            0,
            0,
            "SPEAKER_00",
            "All right, I'll quickly introduce myself. My name is Tushar.",
        ),
        segment(
            1,
            20,
            "SPEAKER_00",
            "Maybe a quick intro about yourself and then I'll explain the process.",
        ),
        segment(
            2,
            28,
            "SPEAKER_01",
            "Sure. I've been working with Amazon for about nine years.",
        ),
        segment(
            3,
            35,
            "SPEAKER_01",
            "I'm currently leading an Amazon Pay charter.",
        ),
    ]

    mapping = SpeakerRoleMapper().map_roles(segments)

    assert mapping.interviewer_speaker_id == "SPEAKER_00"
    assert mapping.candidate_speaker_id == "SPEAKER_01"
    assert mapping.confidence > 0
