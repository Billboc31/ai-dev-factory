"""Tests for T193 — project-scoped isolation of tickets, runs, logs and daemon.

Nine test cases covering:
1. state_dir fix: resolve_state_dir fallback returns state/ not runs/
2. artifact reader isolation: list_tickets reads from project_runtime_root
3. board isolation: get_board reads from project_runtime_root
4. SQLite skip: board skips global DB when project_runtime_root is set
5. supervisor routing for daemon start
6. supervisor routing for daemon stop
7. supervisor routing for daemon status
8. Popen env injection in supervisor project_daemon_start
9. Regression: project action routes pass project_runtime_root to _get_or_404
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from services.control_api.services import artifact_reader, board_service, daemon_manager
from services.control_api.services.runtime_resolver import resolve_state_dir


# ── 1. state_dir fix ──────────────────────────────────────────────────────────

def test_state_dir_fallback_returns_state_not_runs(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    result = resolve_state_dir(tmp_path)
    assert result == tmp_path / "state"
    assert result != tmp_path / "runs"


# ── 2. artifact reader isolation ─────────────────────────────────────────────

def test_artifact_reader_uses_project_runtime_root(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_runtime_root = tmp_path / "runtime" / "my-project"

    # Ticket exists only under project_runtime_root, not under project_root
    run_dir = project_runtime_root / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED"}),
        encoding="utf-8",
    )
    (project_root / "runs").mkdir()

    # Without project_runtime_root: no tickets found
    assert artifact_reader.list_tickets(project_root) == []

    # With project_runtime_root: ticket is found
    tickets = artifact_reader.list_tickets(project_root, project_runtime_root=project_runtime_root)
    assert len(tickets) == 1
    assert tickets[0].ticket_id == "T001"


# ── 3. board isolation ────────────────────────────────────────────────────────

def test_board_service_uses_project_runtime_root(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_runtime_root = tmp_path / "runtime" / "my-project"

    # Ticket exists only under project_runtime_root
    run_dir = project_runtime_root / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"}),
        encoding="utf-8",
    )
    (project_root / "runs").mkdir()

    board_without = board_service.get_board(project_root)
    ticket_ids_without = [
        item.ticket_id
        for col in board_without.columns
        for item in col.items
        if item.ticket_id
    ]
    assert "T001" not in ticket_ids_without

    board_with = board_service.get_board(project_root, project_runtime_root=project_runtime_root)
    ticket_ids_with = [
        item.ticket_id
        for col in board_with.columns
        for item in col.items
        if item.ticket_id
    ]
    assert "T001" in ticket_ids_with


# ── 4. SQLite skip ────────────────────────────────────────────────────────────

def test_board_skips_sqlite_when_project_runtime_root_set(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    import services.control_api.services.board_service as bs

    sqlite_calls: list = []

    def mock_try_load_runtime_db(project_root):
        sqlite_calls.append(project_root)
        return None, None, False

    monkeypatch.setattr(bs, "_try_load_runtime_db", mock_try_load_runtime_db)

    project_root = tmp_path / "project"
    project_root.mkdir()
    project_runtime_root = tmp_path / "runtime" / "my-project"
    (project_runtime_root / "runs").mkdir(parents=True)

    board_service.get_board(project_root, project_runtime_root=project_runtime_root)

    assert sqlite_calls == [], "SQLite must not be queried when project_runtime_root is set"


# ── 5. supervisor routing — start ─────────────────────────────────────────────

def test_daemon_start_routes_to_project_supervisor_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://localhost:8090")
    (tmp_path / "runs").mkdir()

    recorded: list[dict] = []

    def mock_call_supervisor(method, path, json_body=None, timeout=2.0):
        recorded.append({"method": method, "path": path, "body": json_body})
        return {"ok": True, "pid": 12345}, None

    monkeypatch.setattr(daemon_manager, "_call_supervisor", mock_call_supervisor)
    # Ensure get_status (called inside start) also goes to supervisor and reports not running
    monkeypatch.setattr(
        daemon_manager,
        "get_status",
        lambda *a, **kw: daemon_manager.DaemonStatus(running=False),
    )

    daemon_manager.start(tmp_path, "claude", project_id="my-project")

    assert len(recorded) == 1
    assert recorded[0]["path"] == "/projects/my-project/daemon/start"
    assert recorded[0]["method"] == "POST"


# ── 6. supervisor routing — stop ──────────────────────────────────────────────

def test_daemon_stop_routes_to_project_supervisor_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://localhost:8090")

    recorded: list[dict] = []

    def mock_call_supervisor(method, path, json_body=None, timeout=2.0):
        recorded.append({"method": method, "path": path})
        return {"ok": True}, None

    monkeypatch.setattr(daemon_manager, "_call_supervisor", mock_call_supervisor)

    daemon_manager.stop(tmp_path, project_id="my-project")

    assert len(recorded) == 1
    assert recorded[0]["path"] == "/projects/my-project/daemon/stop"
    assert recorded[0]["method"] == "POST"


# ── 7. supervisor routing — status ────────────────────────────────────────────

def test_daemon_status_routes_to_project_supervisor_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://localhost:8090")
    (tmp_path / "runs").mkdir()
    (tmp_path / "logs").mkdir()

    recorded: list[dict] = []

    def mock_call_supervisor(method, path, json_body=None, timeout=2.0):
        recorded.append({"method": method, "path": path})
        return {"running": True, "pid": 42, "started_at": "2026-01-01T00:00:00Z"}, None

    monkeypatch.setattr(daemon_manager, "_call_supervisor", mock_call_supervisor)

    status = daemon_manager.get_status(tmp_path, project_id="my-project")

    assert len(recorded) == 1
    assert recorded[0]["path"] == "/projects/my-project/daemon/status"
    assert status.running is True
    assert status.pid == 42


# ── 8. Popen env injection in supervisor ────────────────────────────────────--

def test_supervisor_project_daemon_start_injects_runtime_root_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    project_root = tmp_path / "my-project"
    project_root.mkdir()
    (project_root / ".git").mkdir()

    from services.supervisor.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    captured_env: dict | None = None

    class FakeProc:
        pid = 9999
        def poll(self):
            return None

    original_popen = subprocess.Popen

    def fake_popen(cmd, **kwargs):
        nonlocal captured_env
        captured_env = kwargs.get("env")
        return FakeProc()

    # Mock _lookup_project_root_from_control_api to return the project root
    import services.supervisor.main as sup_main
    monkeypatch.setattr(sup_main, "_lookup_project_root_from_control_api", lambda pid: str(project_root))

    with patch("subprocess.Popen", side_effect=fake_popen):
        resp = client.post(
            f"/projects/my-project/daemon/start",
            json={"exec_cmd": "claude --dangerously-skip-permissions", "restart_policy": "no-restart"},
        )

    assert resp.status_code == 200
    assert resp.json().get("ok") is True
    assert captured_env is not None
    expected_runtime_root = str(tmp_path / "runtime" / "my-project")
    assert captured_env.get("AI_DEV_FACTORY_RUNTIME_ROOT") == expected_runtime_root


# ── 9. action routes pass project_runtime_root to _get_or_404 ─────────────────

def test_project_action_route_finds_ticket_via_project_runtime_root(tmp_path, monkeypatch):
    """Regression: project action routes must pass project_runtime_root to _get_or_404.

    A ticket whose state.json exists only under project_runtime_root/runs must
    not produce a 404 when a project-scoped action route (approve-plan) is called.
    """
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_PROJECTS_ROOT", raising=False)

    from fastapi.testclient import TestClient
    from services.control_api.main import create_app
    from services.control_api.models.schemas import ActionResult
    import services.control_api.services.subprocess_runner as sr

    factory_root = tmp_path / "factory"
    factory_root.mkdir()
    (factory_root / ".git").mkdir()

    project_root = tmp_path / "my-project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    (project_root / "runs").mkdir()  # empty — T001 is not here

    project_runtime_root = tmp_path / "runtime" / "my-project"
    run_dir = project_runtime_root / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"}),
        encoding="utf-8",
    )

    app = create_app(project_root=factory_root)
    app.state.project_registry.ensure_registered(
        "my-project", project_root, project_runtime_root=project_runtime_root
    )

    ok_result = ActionResult(ok=True, message="approved")
    monkeypatch.setattr(sr, "approve_plan", lambda *a, **kw: ok_result)

    client = TestClient(app)
    r = client.post("/projects/my-project/tickets/T001/approve-plan")

    assert r.status_code == 200, (
        f"Expected 200 but got {r.status_code}: {r.text}. "
        "Action route is missing project_runtime_root in _get_or_404."
    )
