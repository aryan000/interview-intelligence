from abc import ABC, abstractmethod
from uuid import UUID

from interview_intelligence.domain.models import Interview


class InterviewRepository(ABC):
    @abstractmethod
    def save(self, interview: Interview) -> None:
        ...

    @abstractmethod
    def get(self, interview_id: UUID) -> Interview | None:
        ...

    @abstractmethod
    def list_all(self) -> list[Interview]:
        ...
