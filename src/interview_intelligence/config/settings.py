from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the local Interview Intelligence application."""

    model_config = SettingsConfigDict(
        env_prefix="INTERVIEW_INTELLIGENCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Interview Intelligence"
    data_dir: Path = Field(
        default_factory=lambda: Path.home()
        / "Library"
        / "Application Support"
        / "InterviewIntelligence"
    )
    database_filename: str = "app.db"
    max_gpu_jobs: int = 1
    transcription_model: str = "large-v3"

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def recordings_dir(self) -> Path:
        return self.data_dir / "recordings"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_directories(self) -> None:
        for directory in (
            self.data_dir,
            self.recordings_dir,
            self.exports_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
