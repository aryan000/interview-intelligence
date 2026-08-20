from pathlib import Path

from fastapi import FastAPI

from interview_intelligence.api.background import BackgroundProcessingManager
from interview_intelligence.api.routes import build_router
from interview_intelligence.application.existing_interview_coordinator import (
    ExistingInterviewProcessingCoordinator,
)
from interview_intelligence.application.services import build_local_processing_pipeline
from interview_intelligence.config.settings import Settings
from interview_intelligence.jobs.broker import JobEventBroker
from interview_intelligence.jobs.service import ProcessingJobService
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


def create_app(
    database_path: Path | None = None,
    output_root: Path | None = None,
) -> FastAPI:
    settings = Settings()
    settings.ensure_directories()

    database = SQLiteDatabase(database_path or settings.database_path)
    database.initialize()

    app = FastAPI(
        title="Interview Intelligence",
        version="0.1.0",
        description="Local-first interview transcription and feedback intelligence API.",
    )

    interviews = InterviewRepository(database)
    jobs = ProcessingJobRepository(database)
    event_broker = JobEventBroker()
    resolved_output_root = output_root or settings.recordings_dir

    app.state.database = database
    app.state.interviews = interviews
    app.state.jobs = jobs
    app.state.job_event_broker = event_broker

    def coordinator_factory() -> ExistingInterviewProcessingCoordinator:
        return ExistingInterviewProcessingCoordinator(
            pipeline=build_local_processing_pipeline(resolved_output_root),
            interview_repository=interviews,
            job_service=ProcessingJobService(
                jobs,
                listener=event_broker.publish_threadsafe,
            ),
        )

    app.state.background_manager = BackgroundProcessingManager(coordinator_factory)
    app.include_router(build_router())
    return app


app = create_app()
