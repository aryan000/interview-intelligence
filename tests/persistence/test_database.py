from pathlib import Path

from interview_intelligence.persistence.database import SQLiteDatabase


def test_initialize_creates_database(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "app.db")
    database.initialize()

    assert database.path.is_file()

    with database.connect() as connection:
        names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "interviews" in names
    assert "processing_jobs" in names
