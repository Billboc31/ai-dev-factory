"""Tests for the supervisor's ``/sandbox/*`` endpoints.

Architecture validated here:

    Dashboard
      → API container (proxied by services.control_api.routes.sandbox)
        → services/control_api/services/sandbox_runner.py (HTTP client)
          → supervisor (this surface)
            → subprocess.Popen → tools/agent_runner/run_sandbox.py

We mock ``subprocess.Popen`` so the worker is never actually started —
the goal is to verify path mapping, locking, state plumbing, and the
status/logs/stop endpoints. End-to-end worker correctness is the
responsibility of ``test_run_sandbox_worker.py``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))


@pytest.fixture
def supervisor_app(tmp_path, monkeypatch):
    """Boot the supervisor with a tmp runtime root."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(runtime))
    # Force a fresh import so module-level mapper picks up env vars.
    for mod in [m for m in list(sys.modules) if m.startswith("path_mapper") or m == "main"]:
        sys.modules.pop(mod, None)

    from services.supervisor import main as sup_main

    # Reset module state so each test starts clean.
    sup_main._sandbox_locks.clear()
    return sup_main, runtime


# ── Path mapping ──────────────────────────────────────────────────────────────


def test_sandbox_start_logs_container_host_paths(supervisor_app, monkeypatch, caplog):
    """The supervisor must log both the container path and the mapped
    host path. Lack of this log was the symptom that surfaced the bug."""
    import logging as _logging
    sup_main, runtime = supervisor_app
    captured = {}

    class _Stub:
        pid = 12345
        returncode = None

        def wait(self):
            return 0

    def fake_popen(cmd, *a, **kw):
        captured["cmd"] = cmd
        captured["env"] = kw.get("env")
        return _Stub()

    monkeypatch.setattr(sup_main.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sup_main.mapper, "map", lambda p: f"/host{p}")
    caplog.set_level(_logging.INFO, logger="supervisor")

    client = TestClient(sup_main.app)
    resp = client.post(
        "/sandbox/start",
        json={"project_root": "/app", "project_id": "myproject"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    # Worker was invoked with the MAPPED path (not /app).
    assert "/host/app" in captured["cmd"]
    assert "/app" not in [arg for arg in captured["cmd"] if arg == "/app"]

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "supervisor spawning sandbox validation" in log_text
    assert "myproject" in log_text
    assert "/host/app" in log_text


def test_sandbox_start_writes_supervisor_log_header(supervisor_app, monkeypatch):
    """The on-disk log must record the container/host mapping in plain
    text — needed for debugging when caplog is not available."""
    sup_main, runtime = supervisor_app

    class _Stub:
        pid = 23456

        def wait(self):
            return 0

    monkeypatch.setattr(sup_main.subprocess, "Popen", lambda *a, **kw: _Stub())
    monkeypatch.setattr(sup_main.mapper, "map", lambda p: f"/host{p}")

    client = TestClient(sup_main.app)
    client.post("/sandbox/start", json={"project_root": "/app", "project_id": "logtest"})

    log = (runtime / "logs" / "sandbox-logtest.log").read_text()
    assert "supervisor spawning sandbox validation" in log
    assert "project_root(container)=/app" in log
    assert "project_root(host)=/host/app" in log
    assert "sandbox_root(host)=" in log


# ── Locking + PID file ────────────────────────────────────────────────────────


def test_sandbox_start_writes_pid_file(supervisor_app, monkeypatch):
    sup_main, runtime = supervisor_app

    class _Stub:
        pid = 33333

        def wait(self):
            return 0

    monkeypatch.setattr(sup_main.subprocess, "Popen", lambda *a, **kw: _Stub())

    client = TestClient(sup_main.app)
    client.post(
        "/sandbox/start", json={"project_root": "/app", "project_id": "pidtest"}
    )

    pid_path = runtime / "runs" / "sandbox-pidtest.pid"
    assert pid_path.exists()
    data = json.loads(pid_path.read_text())
    assert data["pid"] == 33333


def test_concurrent_start_returns_409(supervisor_app, monkeypatch):
    sup_main, runtime = supervisor_app

    class _LiveStub:
        pid = 44444

        def wait(self):
            return 0

    monkeypatch.setattr(sup_main.subprocess, "Popen", lambda *a, **kw: _LiveStub())
    # Pretend the previously-spawned PID is still alive.
    monkeypatch.setattr(sup_main, "_is_alive", lambda pid: pid == 44444)

    client = TestClient(sup_main.app)
    r1 = client.post(
        "/sandbox/start", json={"project_root": "/app", "project_id": "lock"}
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/sandbox/start", json={"project_root": "/app", "project_id": "lock"}
    )
    assert r2.status_code == 409


# ── Status / logs ─────────────────────────────────────────────────────────────


def test_status_returns_idle_when_no_state_file(supervisor_app):
    sup_main, _runtime = supervisor_app
    client = TestClient(sup_main.app)
    r = client.get("/sandbox/never-ran/status")
    assert r.status_code == 200
    assert r.json() == {"state": "idle"}


def test_status_returns_persisted_state(supervisor_app):
    sup_main, runtime = supervisor_app
    state_path = runtime / "state" / "sandbox-stored.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "state": "success",
        "sandbox_id": "stored-X",
        "started_at": "2026-05-19T10:00:00",
        "finished_at": "2026-05-19T10:01:00",
        "error": None,
        "last_step": "healthcheck.sh",
        "steps": [],
    }))

    client = TestClient(sup_main.app)
    r = client.get("/sandbox/stored/status")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "success"
    assert body["sandbox_id"] == "stored-X"


def test_status_recovers_when_worker_disappeared(supervisor_app, monkeypatch):
    """If state.json says ``running`` but the PID is dead, the status
    endpoint must promote it to ``failed`` so the dashboard recovers."""
    sup_main, runtime = supervisor_app
    state_path = runtime / "state" / "sandbox-ghost.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "state": "running",
        "sandbox_id": "ghost-1",
        "started_at": "2026-05-19T10:00:00",
        "finished_at": None,
        "error": None,
        "last_step": "build.sh",
        "steps": [],
    }))
    pid_path = runtime / "runs" / "sandbox-ghost.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": 999999}))

    monkeypatch.setattr(sup_main, "_is_alive", lambda pid: False)

    client = TestClient(sup_main.app)
    r = client.get("/sandbox/ghost/status")
    body = r.json()
    assert body["state"] == "failed"
    assert "disappeared" in body["error"]


def test_logs_endpoint_returns_lines(supervisor_app):
    sup_main, runtime = supervisor_app
    log = runtime / "logs" / "sandbox-logged.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("line1\nline2\nline3\n")

    client = TestClient(sup_main.app)
    r = client.get("/sandbox/logged/logs", params={"lines": 2})
    assert r.status_code == 200
    assert r.json()["lines"] == ["line2", "line3"]


def test_logs_endpoint_missing_log(supervisor_app):
    sup_main, _runtime = supervisor_app
    client = TestClient(sup_main.app)
    r = client.get("/sandbox/never/logs")
    assert r.json() == {"lines": []}


# ── Stop ──────────────────────────────────────────────────────────────────────


def test_stop_kills_worker_pid(supervisor_app, monkeypatch):
    sup_main, runtime = supervisor_app
    pid_path = runtime / "runs" / "sandbox-stoppable.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": 7777}))

    monkeypatch.setattr(sup_main, "_is_alive", lambda pid: True)
    killed = []
    monkeypatch.setattr(sup_main.os, "kill", lambda pid, sig: killed.append((pid, sig)))

    client = TestClient(sup_main.app)
    r = client.post("/sandbox/stoppable/stop")
    assert r.json() == {"ok": True}
    assert killed == [(7777, sup_main.signal.SIGTERM)]
    assert not pid_path.exists()


def test_stop_when_no_worker(supervisor_app):
    sup_main, _ = supervisor_app
    client = TestClient(sup_main.app)
    r = client.post("/sandbox/nothing/stop")
    body = r.json()
    assert body["ok"] is False
    assert body["error"] == "not_running"
