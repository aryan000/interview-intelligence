from typing import cast

from fastapi import Request

from interview_intelligence.api.background import BackgroundProcessingManager
from interview_intelligence.jobs.broker import JobEventBroker
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


def interviews(request: Request) -> InterviewRepository:
    return cast(InterviewRepository, request.app.state.interviews)


def jobs(request: Request) -> ProcessingJobRepository:
    return cast(ProcessingJobRepository, request.app.state.jobs)


def broker(request: Request) -> JobEventBroker:
    return cast(JobEventBroker, request.app.state.job_event_broker)


def background_manager(request: Request) -> BackgroundProcessingManager:
    return cast(BackgroundProcessingManager, request.app.state.background_manager)
