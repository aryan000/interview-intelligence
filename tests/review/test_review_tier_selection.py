from pathlib import Path

from fastapi.testclient import TestClient

from interview_intelligence.api.app import create_app


def test_review_config_defaults_to_luna(tmp_path: Path) -> None:
    app = create_app(tmp_path / "app.db", tmp_path / "output")
    client = TestClient(app)

    response = client.get("/api/v1/review/config")

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-5.6-luna"
