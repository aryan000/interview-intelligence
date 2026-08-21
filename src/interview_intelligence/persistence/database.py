import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS interviews (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    recruiter_or_interviewer TEXT NOT NULL,
    interview_datetime TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    role TEXT,
    target_level TEXT,
    round_type TEXT,
    source_audio_path TEXT NOT NULL,
    artifact_root_path TEXT,
    transcription_seconds REAL,
    diarization_seconds REAL,
    total_processing_seconds REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    interview_id TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    progress_percent REAL NOT NULL DEFAULT 0,
    processed_audio_seconds REAL NOT NULL DEFAULT 0,
    total_audio_seconds REAL NOT NULL DEFAULT 0,
    message TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_interview_id
ON processing_jobs(interview_id);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
ON processing_jobs(status);
"""


INTERVIEW_MIGRATIONS: dict[str, str] = {
    "round_type": "ALTER TABLE interviews ADD COLUMN round_type TEXT",
    "transcription_seconds": (
        "ALTER TABLE interviews ADD COLUMN transcription_seconds REAL"
    ),
    "diarization_seconds": (
        "ALTER TABLE interviews ADD COLUMN diarization_seconds REAL"
    ),
    "total_processing_seconds": (
        "ALTER TABLE interviews ADD COLUMN total_processing_seconds REAL"
    ),
}


class SQLiteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._apply_interview_migrations(connection)

    @staticmethod
    def _apply_interview_migrations(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(interviews)"
            ).fetchall()
        }

        for column, statement in INTERVIEW_MIGRATIONS.items():
            if column not in columns:
                connection.execute(statement)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
