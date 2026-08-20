from uuid import uuid4

import pytest

from interview_intelligence.api.background import BackgroundProcessingManager


class StubCoordinator:
    def __init__(self, calls: list[tuple[object, object]]) -> None:
        self.calls = calls

    def run(self, interview_id, job_id):
        self.calls.append((interview_id, job_id))


@pytest.mark.anyio
async def test_background_manager_runs_coordinator() -> None:
    calls: list[tuple[object, object]] = []
    manager = BackgroundProcessingManager(
        lambda: StubCoordinator(calls)  # type: ignore[arg-type]
    )
    interview_id = uuid4()
    job_id = uuid4()

    task = manager.start(interview_id, job_id)
    await task

    assert calls == [(interview_id, job_id)]
