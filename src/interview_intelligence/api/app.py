from pathlib import Path

from fastapi import FastAPI

from interview_intelligence.api.routes import build_router
from interview_intelligence.config.settings import Settings
from interview_intelligence.persistence.database import SQLiteDatabase
from interview_intelligence.persistence.repositories import (
    InterviewRepository,
    ProcessingJobRepository,
)


def create_app(
    database_path: Path | None = None,
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

    app.state.database = database
    app.state.interviews = InterviewRepository(database)
    app.state.jobs = ProcessingJobRepository(database)

    app.include_router(build_router())
    return app


app = create_app()
