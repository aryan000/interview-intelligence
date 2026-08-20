from abc import ABC, abstractmethod

from interview_intelligence.review.models import InterviewReview, ReviewRequest


class InterviewReviewEngine(ABC):
    @abstractmethod
    def review(
        self,
        request: ReviewRequest,
        transcript: str,
    ) -> InterviewReview:
        """Review one interview transcript and return structured feedback."""
