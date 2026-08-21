import asyncio
import inspect
from collections.abc import Callable
from threading import Event
from uuid import UUID

from interview_intelligence.application.existing_interview_coordinator import (
    ExistingInterviewProcessingCoordinator,
)


class BackgroundProcessingManager:
    """Run blocking ML processing outside FastAPI request handlers.

    Cancellation is cooperative: the worker receives a cancellation Event and
    stops at the next pipeline progress boundary. A single blocking ML call
    cannot be force-killed safely from a Python thread.
    """

    def __init__(
        self,
        coordinator_factory: Callable[..., ExistingInterviewProcessingCoordinator],
    ) -> None:
        self.coordinator_factory = coordinator_factory
        self._tasks: dict[UUID, asyncio.Task[None]] = {}
        self._cancel_events: dict[UUID, Event] = {}

    def start(self, interview_id: UUID, job_id: UUID) -> asyncio.Task[None]:
        existing = self._tasks.get(interview_id)
        if existing is not None and not existing.done():
            raise RuntimeError("Interview is already being processed")

        cancel_event = Event()
        self._cancel_events[interview_id] = cancel_event

        task = asyncio.create_task(
            self._run(interview_id, job_id, cancel_event)
        )
        self._tasks[interview_id] = task
        task.add_done_callback(
            lambda _: self._cleanup(interview_id)
        )
        return task

    def is_active(self, interview_id: UUID) -> bool:
        task = self._tasks.get(interview_id)
        return task is not None and not task.done()

    def request_cancel(self, interview_id: UUID) -> bool:
        event = self._cancel_events.get(interview_id)
        if event is None or not self.is_active(interview_id):
            return False
        event.set()
        return True

    def _cleanup(self, interview_id: UUID) -> None:
        self._tasks.pop(interview_id, None)
        self._cancel_events.pop(interview_id, None)

    async def _run(
        self,
        interview_id: UUID,
        job_id: UUID,
        cancel_event: Event,
    ) -> None:
        parameters = inspect.signature(self.coordinator_factory).parameters
        coordinator = (
            self.coordinator_factory()
            if len(parameters) == 0
            else self.coordinator_factory(cancel_event)
        )
        await asyncio.to_thread(coordinator.run, interview_id, job_id)
