"""Tests for main Control API endpoints — health, daemon status, ticket listing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _make_app(tmp_path: Path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path)


def _make_ticket(tmp_path: Path, ticket_id: str, state: str) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}-work"}),
        encoding="utf-8",
    )


# ── /health ───────────────────────────────────────────────────────────────────

def test_health(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── /daemon/status ────────────────────────────────────────────────────────────

def test_daemon_status_not_running(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/daemon/status")
    assert r.status_code == 200
    assert r.json()["running"] is False


def test_daemon_status_running(tmp_path):
    import os
    (tmp_path / "runs").mkdir()
    pid = os.getpid()
    pid_data = {"pid": pid, "started_at": "2026-01-01T00:00:00Z"}
    (tmp_path / "runs" / "daemon.pid").write_text(json.dumps(pid_data))
    client = TestClient(_make_app(tmp_path))
    r = client.get("/daemon/status")
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is True
    assert body["pid"] == pid


# ── /tickets ──────────────────────────────────────────────────────────────────

def test_list_tickets_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets")
    assert r.status_code == 200
    assert r.json() == []


def test_list_tickets(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    _make_ticket(tmp_path, "T002", "TEST_COMPLETE")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets")
    assert r.status_code == 200
    ids = [t["ticket_id"] for t in r.json()]
    assert "T001" in ids
    assert "T002" in ids


def test_get_ticket(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    assert r.json()["ticket_id"] == "T001"
    assert r.json()["state"] == "PLAN_APPROVED"


def test_get_ticket_not_found(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T999")
    assert r.status_code == 404


def test_get_ticket_invalid_id(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/INVALID")
    assert r.status_code == 422


def test_get_logs(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    (tmp_path / "runs" / "T001" / "runtime.log").write_text("log line\n")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/logs")
    assert r.status_code == 200
    assert "log line" in r.text


def test_get_logs_not_found(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/logs")
    assert r.status_code == 404


def test_get_artifacts(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    (tmp_path / "runs" / "T001" / "plan.md").write_text("plan content")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/artifacts")
    assert r.status_code == 200
    assert "plan.md" in r.json()


def test_get_plan(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    (tmp_path / "runs" / "T001" / "plan.md").write_text("# Plan")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/plan")
    assert r.status_code == 200
    assert "# Plan" in r.text


def test_get_plan_not_found(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/plan")
    assert r.status_code == 404


# ── /daemon/activity ─────────────────────────────────────────────────────────

def test_daemon_activity_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/daemon/activity")
    assert r.status_code == 200
    assert r.json() == {"lines": []}


def test_daemon_activity_with_log(tmp_path):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "daemon.log").write_text(
        "[10:41:02] daemon started\n[10:41:18] T030 planner started\n"
    )
    client = TestClient(_make_app(tmp_path))
    r = client.get("/daemon/activity")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert len(lines) == 2
    assert "[10:41:02] daemon started" in lines


def test_daemon_activity_lines_limit(tmp_path):
    (tmp_path / "runs").mkdir()
    log_content = "\n".join(f"line {i}" for i in range(100)) + "\n"
    (tmp_path / "runs" / "daemon.log").write_text(log_content)
    client = TestClient(_make_app(tmp_path))
    r = client.get("/daemon/activity?lines=10")
    assert r.status_code == 200
    assert len(r.json()["lines"]) == 10


# ── /providers/status ─────────────────────────────────────────────────────────

def test_providers_status(tmp_path):
    client = TestClient(_make_app(tmp_path))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        r = client.get("/providers/status")
    assert r.status_code == 200
    providers = r.json()
    assert isinstance(providers, list)
    names = [p["name"] for p in providers]
    assert "github" in names


# ── /projects ────────────────────────────────────────────────────────────────

def test_list_projects(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/projects")
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) == 1
    assert projects[0]["tickets_count"] == 0
