"""Tests for runtime dashboard API endpoints (T139)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _make_app(tmp_path: Path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path)


def _make_sandbox(
    tmp_path: Path,
    sandbox_id: str,
    state: str,
    pid: int | None = None,
) -> Path:
    sandbox_dir = tmp_path / "sandboxes" / sandbox_id
    sandbox_dir.mkdir(parents=True)
    (sandbox_dir / "state.json").write_text(
        json.dumps({
            "state": state,
            "project_id": "test-project",
            "sandbox_id": sandbox_id,
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": None,
            "ports": {},
            "worktree_path": None,
            "compose_project": None,
        }),
        encoding="utf-8",
    )
    if pid is not None:
        (sandbox_dir / "daemon.lock").write_text(
            json.dumps({"pid": pid, "created_at": "2026-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
    return sandbox_dir


def _make_proposal(tmp_path: Path, proposal_id: str, status: str) -> Path:
    proposal_dir = tmp_path / "runs" / "auto-fix" / "proposals" / proposal_id
    proposal_dir.mkdir(parents=True)
    (proposal_dir / "state.json").write_text(
        json.dumps({
            "proposal_id": proposal_id,
            "sandbox_id": "sb-001",
            "status": status,
            "changed_files_count": 3,
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T01:00:00Z",
        }),
        encoding="utf-8",
    )
    return proposal_dir


# ── GET /runtime-dashboard/sandbox-runs ──────────────────────────────────────

def test_list_sandbox_runs_empty(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sandbox_runs_returns_required_fields(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "completed")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    item = data[0]
    assert item["id"] == "sb-001"
    assert item["status"] == "completed"
    assert "started_at" in item
    assert "worktree_path" in item
    assert "ports" in item


# ── GET /runtime-dashboard/sandbox-runs/{id}/logs ────────────────────────────

def test_get_sandbox_logs_not_found(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs/nonexistent/logs")
    assert r.status_code == 404


def test_get_sandbox_logs_no_log_file(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "completed")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs/sb-001/logs")
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == ""
    assert body["next_offset"] == 0


def test_get_sandbox_logs_returns_content(tmp_path):
    sandbox_dir = _make_sandbox(tmp_path, "sb-001", "completed")
    (sandbox_dir / "run.log").write_text("line1\nline2\nline3\n", encoding="utf-8")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs/sb-001/logs")
    assert r.status_code == 200
    body = r.json()
    assert "line1" in body["content"]
    assert body["next_offset"] > 0


def test_get_sandbox_logs_respects_offset(tmp_path):
    sandbox_dir = _make_sandbox(tmp_path, "sb-001", "completed")
    (sandbox_dir / "run.log").write_text("0123456789", encoding="utf-8")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/sandbox-runs/sb-001/logs", params={"offset": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "56789"
    assert body["next_offset"] == 10


# ── DELETE /runtime-dashboard/sandbox-runs/{id} ──────────────────────────────

def test_delete_sandbox_run_not_found(tmp_path):
    (tmp_path / "sandboxes").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/sandbox-runs/nonexistent")
    assert r.status_code == 404


def test_delete_sandbox_run_completed_returns_204(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "completed")
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/sandbox-runs/sb-001")
    assert r.status_code == 204
    assert not (tmp_path / "sandboxes" / "sb-001").exists()


def test_delete_sandbox_run_running_returns_409(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "running")
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/sandbox-runs/sb-001")
    assert r.status_code == 409
    assert "active" in r.json()["detail"]


def test_delete_sandbox_run_live_pid_returns_409(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "completed", pid=os.getpid())
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/sandbox-runs/sb-001")
    assert r.status_code == 409
    assert "live" in r.json()["detail"]


def test_delete_sandbox_run_stale_pid_returns_204(tmp_path):
    _make_sandbox(tmp_path, "sb-001", "completed", pid=999_999_999)
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/sandbox-runs/sb-001")
    assert r.status_code == 204


# ── GET /runtime-dashboard/proposal-runs ─────────────────────────────────────

def test_list_proposal_runs_empty(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/proposal-runs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_proposal_runs_returns_required_fields(tmp_path):
    _make_proposal(tmp_path, "prop-001", "completed")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/proposal-runs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    item = data[0]
    assert item["proposal_id"] == "prop-001"
    assert item["status"] == "completed"
    assert "sandbox_id" in item
    assert "changed_files_count" in item


# ── DELETE /runtime-dashboard/proposal-runs/{id} ─────────────────────────────

def test_delete_proposal_run_completed_returns_204(tmp_path):
    _make_proposal(tmp_path, "prop-001", "completed")
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/proposal-runs/prop-001")
    assert r.status_code == 204


def test_delete_proposal_run_active_returns_409(tmp_path):
    _make_proposal(tmp_path, "prop-001", "running")
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/proposal-runs/prop-001")
    assert r.status_code == 409
    assert "active" in r.json()["detail"]


def test_delete_proposal_run_not_found(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.delete("/runtime-dashboard/proposal-runs/nonexistent")
    assert r.status_code == 404


# ── GET /runtime-dashboard/health ────────────────────────────────────────────

def test_get_runtime_health_returns_required_keys(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/health")
    assert r.status_code == 200
    body = r.json()
    assert "supervisor_status" in body
    assert "active_jobs" in body
    assert "stale_pid_files" in body
    assert "stale_locks" in body


def test_get_runtime_health_stale_lock_detected(tmp_path):
    runs_dir = tmp_path / "runs"
    lock_dir = runs_dir / "T001"
    lock_dir.mkdir(parents=True)
    (lock_dir / "daemon.lock").write_text(
        json.dumps({"pid": 999_999_999, "created_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/health")
    body = r.json()
    assert len(body["stale_locks"]) == 1
    assert "T001/daemon.lock" in body["stale_locks"][0]


def test_get_runtime_health_live_lock_counted_as_active(tmp_path):
    runs_dir = tmp_path / "runs"
    lock_dir = runs_dir / "T001"
    lock_dir.mkdir(parents=True)
    (lock_dir / "daemon.lock").write_text(
        json.dumps({"pid": os.getpid(), "created_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/health")
    body = r.json()
    assert body["active_jobs"] == 1
    assert len(body["stale_locks"]) == 0


def test_get_runtime_health_stale_pid_file_detected(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    (runs_dir / "daemon.pid").write_text(
        json.dumps({"pid": 999_999_999, "started_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    client = TestClient(_make_app(tmp_path))
    r = client.get("/runtime-dashboard/health")
    body = r.json()
    assert len(body["stale_pid_files"]) == 1
    assert "daemon.pid" in body["stale_pid_files"][0]
