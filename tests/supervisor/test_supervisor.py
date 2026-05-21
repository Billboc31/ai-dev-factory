"""Tests for the host-side supervisor and its control-API delegation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import services.supervisor.main as sup_mod
from services.supervisor.main import app as supervisor_app


# ── 1. Supervisor app: GET /health ───────────────────────────────────────────

def test_health_ok(monkeypatch, tmp_path):
    """GET /health returns 200 and status == ok."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    client = TestClient(supervisor_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── 2. Supervisor app: GET /daemon/status (no PID file) ──────────────────────

def test_daemon_status_not_running(monkeypatch, tmp_path):
    """GET /daemon/status returns running=False when no PID file exists."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    client = TestClient(supervisor_app)
    resp = client.get("/daemon/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False
    assert data["pid"] is None


# ── 3. daemon_manager.start() delegates to supervisor ────────────────────────

def test_start_delegates_to_supervisor(monkeypatch, tmp_path):
    """daemon_manager.start() calls supervisor and does NOT call subprocess.Popen."""
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://localhost:8090")
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)

    from services.control_api.services import daemon_manager as dm

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "pid": 12345}

    with patch.object(dm, "get_status") as mock_get_status, \
         patch("httpx.Client") as mock_client_cls, \
         patch.object(dm.subprocess, "Popen") as mock_popen:

        mock_get_status.return_value = MagicMock(running=False, pid=None)

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = mock_response
        mock_client_cls.return_value = mock_ctx

        result = dm.start(tmp_path, "claude --dangerously-skip-permissions")

    assert result.ok is True
    mock_popen.assert_not_called()
    mock_ctx.post.assert_called_once()
    called_url = mock_ctx.post.call_args[0][0]
    assert "/daemon/start" in called_url


# ── 4. daemon_manager.start() returns structured error when unreachable ───────

def test_supervisor_unreachable_returns_structured_error(monkeypatch, tmp_path):
    """When supervisor is unreachable, start() returns error='supervisor_unreachable'."""
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://localhost:8090")
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setenv("AI_DEV_FACTORY_PROJECT_ROOT", str(tmp_path))

    from services.control_api.services import daemon_manager as dm

    with patch.object(dm, "get_status") as mock_get_status, \
         patch("httpx.Client") as mock_client_cls:

        mock_get_status.return_value = MagicMock(running=False, pid=None)

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_ctx

        result = dm.start(tmp_path, "claude --dangerously-skip-permissions")

    assert result.ok is False
    assert result.error == "supervisor_unreachable"
    assert result.host_command is not None
    assert "start_supervisor" in result.host_command


# ── 5. Unexpected daemon exit sets exit_unexpected=True ───────────────────────

def test_unexpected_exit_detected(monkeypatch, tmp_path):
    """Simulating an unexpected daemon exit sets exit_unexpected=True."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())
    monkeypatch.setattr(sup_mod, "_daemon_proc", None)
    monkeypatch.setattr(sup_mod, "_voluntary_stop", False)

    # Simulate a daemon that was running but the process is now gone
    dead_pid = 999999
    sup_mod._daemon_state.pid = dead_pid

    pid_path = tmp_path / "runs" / "daemon.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": dead_pid, "started_at": "2026-01-01T00:00:00Z"}))

    sup_mod._check_and_maybe_restart()

    assert sup_mod._daemon_state.pid is None
    assert sup_mod._daemon_state.exit_unexpected is True
    assert not pid_path.exists()


# ── 6. Stale PID file is removed and status returns running=False ─────────────

def test_stale_pid_recovery(monkeypatch, tmp_path):
    """GET /daemon/status removes a stale PID file and returns running=False."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())

    pid_path = tmp_path / "runs" / "daemon.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": 999999, "started_at": "2026-01-01T00:00:00Z"}))

    client = TestClient(supervisor_app)
    resp = client.get("/daemon/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False
    assert not pid_path.exists()


# ── 7. Restart-on-crash policy relaunches the daemon ─────────────────────────

def test_restart_on_crash_policy(monkeypatch, tmp_path):
    """restart-on-crash policy increments restart_count and respawns the daemon."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())
    monkeypatch.setattr(sup_mod, "_daemon_proc", None)
    monkeypatch.setattr(sup_mod, "_voluntary_stop", False)
    monkeypatch.setattr(sup_mod, "_daemon_exec_cmd", "echo test")

    sup_mod._daemon_state.pid = 999999
    sup_mod._daemon_state.restart_policy = "restart-on-crash"

    spawned: list[str] = []

    def mock_spawn(exec_cmd: str):
        spawned.append(exec_cmd)
        return 42000, "2026-01-01T01:00:00Z", None

    monkeypatch.setattr(sup_mod, "_spawn_daemon", mock_spawn)

    sup_mod._check_and_maybe_restart()

    assert sup_mod._daemon_state.restart_count == 1
    assert sup_mod._daemon_state.pid == 42000
    assert len(spawned) == 1


# ── 8. Voluntary stop is not flagged as unexpected ────────────────────────────

def test_voluntary_stop_not_flagged_unexpected(monkeypatch, tmp_path):
    """Stopping via API (voluntary_stop=True) does not set exit_unexpected."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())
    monkeypatch.setattr(sup_mod, "_daemon_proc", None)
    monkeypatch.setattr(sup_mod, "_voluntary_stop", True)

    sup_mod._daemon_state.pid = 999999

    sup_mod._check_and_maybe_restart()

    assert sup_mod._daemon_state.exit_unexpected is False
    assert sup_mod._voluntary_stop is False


# ── 9. daemon_stop clears pid immediately (stop/start race fix) ───────────────

def test_daemon_stop_clears_pid_immediately(monkeypatch, tmp_path):
    """POST /daemon/stop clears pid/started_at in-memory before returning."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())

    live_pid = os.getpid()  # use our own PID — guaranteed alive
    sup_mod._daemon_state.pid = live_pid
    sup_mod._daemon_state.started_at = "2026-01-01T00:00:00Z"

    client = TestClient(supervisor_app)

    with patch.object(sup_mod.os, "kill") as mock_kill:
        mock_kill.return_value = None
        resp = client.post("/daemon/stop")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert sup_mod._daemon_state.pid is None
    assert sup_mod._daemon_state.started_at is None


# ── 10. Lifespan restores exec_cmd and restart_policy from PID file ───────────

def test_lifespan_restores_exec_cmd_and_restart_policy(monkeypatch, tmp_path):
    """On supervisor restart, exec_cmd and restart_policy are loaded from the PID file."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(sup_mod, "_daemon_state", sup_mod.DaemonState())
    monkeypatch.setattr(sup_mod, "_daemon_exec_cmd", "claude --dangerously-skip-permissions")

    live_pid = os.getpid()
    pid_path = tmp_path / "runs" / "daemon.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({
        "pid": live_pid,
        "started_at": "2026-01-01T00:00:00Z",
        "exec_cmd": "my-custom-cmd --flag",
        "restart_policy": "restart-on-crash",
    }))

    with TestClient(supervisor_app):
        assert sup_mod._daemon_state.restart_policy == "restart-on-crash"
        assert sup_mod._daemon_exec_cmd == "my-custom-cmd --flag"
