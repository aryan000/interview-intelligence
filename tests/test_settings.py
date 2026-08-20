from pathlib import Path

from interview_intelligence.config.settings import Settings


def test_database_path_is_inside_data_directory(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)

    assert settings.database_path == tmp_path / "app.db"


def test_ensure_directories_creates_expected_directories(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)

    settings.ensure_directories()

    assert settings.recordings_dir.is_dir()
    assert settings.exports_dir.is_dir()
    assert settings.logs_dir.is_dir()
