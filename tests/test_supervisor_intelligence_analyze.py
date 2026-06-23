"""Supervisor ticket-intelligence analyze endpoint tests."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import runtime_db as _runtime_db  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    project_root = tmp_path / "clone"
    project_root.mkdir()
    (project_root / "runs" / "T001").mkdir(parents=True)
    (project_root / "runs" / "T001" / "ticket.md").write_text("# T001\n", encoding="utf-8")
    (project_root / "runs" / "T001" / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED"}),
        encoding="utf-8",
    )

    db = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    _runtime_db.init_runtime_db(db)

    from services.supervisor.main import app

    with patch("services.supervisor.main._lookup_project_root_from_control_api", return_value=str(project_root)):
        with patch("services.supervisor.main._project_runtime_root", return_value=tmp_path):
            yield TestClient(app), db, project_root


def test_supervisor_analyze_starts_when_row_already_queued(client):
    """API may pre-exist a `queued` row; supervisor must still launch the analyzer."""
    test_client, db, _project_root = client
    _runtime_db.upsert_ticket_intelligence(db, "T001", analysis_status="queued")

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        resp = test_client.post(
            "/projects/P1/tickets/T001/intelligence/analyze",
            json={},
        )

    assert resp.status_code == 200
    assert resp.json()["analysis_status"] == "queued"
    time.sleep(0.1)
    mock_run.assert_called_once()


def test_supervisor_analyze_short_circuits_when_running(client):
    """Duplicate analyze while already running must not spawn a second thread."""
    test_client, db, _project_root = client
    _runtime_db.upsert_ticket_intelligence(db, "T001", analysis_status="running")

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        resp = test_client.post(
            "/projects/P1/tickets/T001/intelligence/analyze",
            json={},
        )

    assert resp.status_code == 200
    assert resp.json()["analysis_status"] == "running"
    mock_run.assert_not_called()
