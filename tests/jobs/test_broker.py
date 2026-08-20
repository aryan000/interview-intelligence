import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from interview_intelligence.domain.enums import JobStage, JobStatus
from interview_intelligence.jobs.broker import JobEventBroker
from interview_intelligence.jobs.events import JobProgressEvent


@pytest.mark.anyio
async def test_broker_publishes_to_subscriber() -> None:
    broker = JobEventBroker()
    broker.bind_loop(asyncio.get_running_loop())
    job_id = uuid4()
    queue = broker.subscribe(job_id)

    event = JobProgressEvent(
        job_id=job_id,
        interview_id=uuid4(),
        status=JobStatus.RUNNING,
        stage=JobStage.TRANSCRIPTION,
        progress_percent=50,
        processed_audio_seconds=60,
        total_audio_seconds=120,
        message="Transcribing",
        occurred_at=datetime.now(UTC),
    )

    broker.publish_threadsafe(event)
    received = await asyncio.wait_for(queue.get(), timeout=1)

    assert received == event
    broker.unsubscribe(job_id, queue)
