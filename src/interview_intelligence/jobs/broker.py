import asyncio
from collections import defaultdict
from uuid import UUID

from interview_intelligence.jobs.events import JobProgressEvent


class JobEventBroker:
    """In-memory fan-out of job progress events to WebSocket subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[asyncio.Queue[JobProgressEvent]]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def publish(self, event: JobProgressEvent) -> None:
        for queue in tuple(self._subscribers.get(event.job_id, ())):
            await queue.put(event)

    def publish_threadsafe(self, event: JobProgressEvent) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(
            asyncio.create_task,
            self.publish(event),
        )

    def subscribe(self, job_id: UUID) -> asyncio.Queue[JobProgressEvent]:
        queue: asyncio.Queue[JobProgressEvent] = asyncio.Queue()
        self._subscribers[job_id].add(queue)
        return queue

    def unsubscribe(
        self,
        job_id: UUID,
        queue: asyncio.Queue[JobProgressEvent],
    ) -> None:
        subscribers = self._subscribers.get(job_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(job_id, None)
