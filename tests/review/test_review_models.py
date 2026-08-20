from interview_intelligence.review.models import (
    HiringSignal,
    InterviewReview,
    QuestionReview,
)


def test_interview_review_supports_structured_question_feedback() -> None:
    review = InterviewReview(
        interview_id="interview-1",
        provider="stub",
        model="stub-model",
        overall_summary="Good architecture depth with some prioritization gaps.",
        hiring_signal=HiringSignal.HIRE,
        confidence=0.8,
        strengths=["Strong system decomposition"],
        concerns=["Could quantify trade-offs earlier"],
        improvement_areas=["Prioritization"],
        questions=[
            QuestionReview(
                sequence_number=1,
                question="How would you design the system?",
                question_start_seconds=120,
                answer_summary="Candidate decomposed the system into core services.",
                strengths=["Clear boundaries"],
                gaps=["Capacity estimates were late"],
                rating=4,
                level_signal="Staff-leaning",
            )
        ],
    )

    assert review.hiring_signal == HiringSignal.HIRE
    assert review.questions[0].rating == 4
