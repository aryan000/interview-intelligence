import sqlite3
from pathlib import Path

from interview_intelligence.persistence.database import SQLiteDatabase


def test_initialize_migrates_existing_interviews_table(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE interviews (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                recruiter_or_interviewer TEXT NOT NULL,
                interview_datetime TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                role TEXT,
                target_level TEXT,
                source_audio_path TEXT NOT NULL,
                artifact_root_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    database = SQLiteDatabase(database_path)
    database.initialize()

    with database.connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(interviews)"
            ).fetchall()
        }

    assert "round_type" in columns
    assert "transcription_seconds" in columns
    assert "diarization_seconds" in columns
    assert "total_processing_seconds" in columns
