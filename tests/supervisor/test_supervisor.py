"""Tests for the host-side supervisor and its control-API delegation."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
