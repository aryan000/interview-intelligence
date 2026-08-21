import argparse
import sqlite3
from pathlib import Path

import pytest

from interview_intelligence.review.benchmark import (
    _load_interview,
    _parse_models,
    _safe_model_name,
)


def test_parse_models() -> None:
    assert _parse_models("gpt-a, gpt-b") == ["gpt-a", "gpt-b"]


def test_parse_models_rejects_empty_value() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_models(" , ")


def test_safe_model_name() -> None:
    assert _safe_model_name("provider/model:v1") == "provider-model-v1"


def test_load_interview_from_existing_database(tmp_path: Path) -> None:
    database = tmp_path / "app.db"
    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE interviews (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                role TEXT,
                target_level TEXT,
                round_type TEXT,
                artifact_root_path TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO interviews (
                id, company, role, target_level, round_type, artifact_root_path
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "abc",
                "PhonePe",
                "Engineering Manager",
                "L6",
                "HLD",
                str(artifact_root),
            ),
        )

    result = _load_interview(database, "abc")

    assert result.id == "abc"
    assert result.company == "PhonePe"
    assert result.round_type == "HLD"
    assert result.artifact_root_path == artifact_root
