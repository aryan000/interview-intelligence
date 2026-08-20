import asyncio
from collections.abc import Callable
from uuid import UUID

from interview_intelligence.application.existing_interview_coordinator import (
    ExistingInterviewProcessingCoordinator,
)


class BackgroundProcessingManager:
    """Run blocking ML processing outside FastAPI request handlers."""

    def __init__(
        self,
        coordinator_factory: Callable[[], ExistingInterviewProcessingCoordinator],
    ) -> None:
        self.coordinator_factory = coordinator_factory
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    def start(self, interview_id: UUID, job_id: UUID) -> asyncio.Task[None]:
        existing = self._tasks.get(interview_id)
        if existing is not None and not existing.done():
            raise RuntimeError("Interview is already being processed")

        task = asyncio.create_task(self._run(interview_id, job_id))
        self._tasks[interview_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(interview_id, None))
        return task

    async def _run(self, interview_id: UUID, job_id: UUID) -> None:
        coordinator = self.coordinator_factory()
        await asyncio.to_thread(coordinator.run, interview_id, job_id)
