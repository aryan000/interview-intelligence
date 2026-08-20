from dataclasses import dataclass

from interview_intelligence.domain.models import TranscriptSegment


@dataclass(frozen=True)
class SpeakerRoleMapping:
    candidate_speaker_id: str | None
    interviewer_speaker_id: str | None
    confidence: float
    reason: str


class SpeakerRoleMapper:
    """Infer Candidate/Interviewer from early interview semantics.

    This is intentionally conservative. It only maps when the first minutes
    contain a clear interviewer-introduction pattern and a separate candidate
    work-history introduction.
    """

    INTERVIEWER_PHRASES = (
        "i'll quickly introduce myself",
        "i will quickly introduce myself",
        "i'll explain the process",
        "i will explain the process",
        "quick intro about yourself",
        "tell me about yourself",
        "my name is",
    )

    CANDIDATE_PHRASES = (
        "i have been working with",
        "i've been working with",
        "i work with",
        "i joined",
        "currently leading",
        "i have worked",
        "i've worked",
    )

    def map_roles(
        self,
        segments: list[TranscriptSegment],
        analysis_window_seconds: float = 180.0,
    ) -> SpeakerRoleMapping:
        speaker_text: dict[str, list[str]] = {}

        for segment in segments:
            if segment.start_seconds > analysis_window_seconds:
                break
            if segment.speaker_id is None:
                continue
            speaker_text.setdefault(segment.speaker_id, []).append(segment.text.lower())

        if len(speaker_text) < 2:
            return SpeakerRoleMapping(
                candidate_speaker_id=None,
                interviewer_speaker_id=None,
                confidence=0.0,
                reason="fewer than two speakers with text in analysis window",
            )

        scores: dict[str, tuple[int, int]] = {}
        for speaker_id, texts in speaker_text.items():
            joined = " ".join(texts)
            interviewer_score = sum(
                1 for phrase in self.INTERVIEWER_PHRASES if phrase in joined
            )
            candidate_score = sum(
                1 for phrase in self.CANDIDATE_PHRASES if phrase in joined
            )
            scores[speaker_id] = (interviewer_score, candidate_score)

        interviewer = max(scores, key=lambda speaker: scores[speaker][0])
        remaining = [speaker for speaker in scores if speaker != interviewer]
        candidate = max(remaining, key=lambda speaker: scores[speaker][1])

        interviewer_score = scores[interviewer][0]
        candidate_score = scores[candidate][1]

        if interviewer_score == 0 or candidate_score == 0:
            return SpeakerRoleMapping(
                candidate_speaker_id=None,
                interviewer_speaker_id=None,
                confidence=0.0,
                reason="semantic evidence was insufficient for safe automatic mapping",
            )

        confidence = min(1.0, (interviewer_score + candidate_score) / 6.0)

        return SpeakerRoleMapping(
            candidate_speaker_id=candidate,
            interviewer_speaker_id=interviewer,
            confidence=confidence,
            reason=(
                f"interviewer semantic score={interviewer_score}, "
                f"candidate semantic score={candidate_score}"
            ),
        )
