"""Integration tests for project-scoped runtime API endpoints.

Tests spin up two isolated project roots and verify that:
- /projects/{id}/daemon/status, /tickets, and /project-map respond independently
- Unknown project_id returns HTTP 404
- Legacy routes (/daemon/*, /tickets/*) still work
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _make_multi_app(tmp_path: Path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.control_api.main import create_app

    proj_a = tmp_path / "project-a"
    proj_b = tmp_path / "project-b"
    for p in (proj_a, proj_b):
        p.mkdir()
        (p / ".git").mkdir()

    return create_app(project_root=proj_a, projects_root=tmp_path), proj_a, proj_b


def _make_ticket(project_root: Path, ticket_id: str, state: str) -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}-work"}),
        encoding="utf-8",
    )


# ── unknown project → 404 ─────────────────────────────────────────────────────

def test_unknown_project_daemon_status_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, _ = _make_multi_app(tmp_path)
    (proj_a / "runs").mkdir(exist_ok=True)
    client = TestClient(app)
    r = client.get("/projects/no-such-project/daemon/status")
    assert r.status_code == 404


def test_unknown_project_tickets_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, _ = _make_multi_app(tmp_path)
    (proj_a / "runs").mkdir(exist_ok=True)
    client = TestClient(app)
    r = client.get("/projects/no-such-project/tickets")
    assert r.status_code == 404


def test_unknown_project_project_map_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, _ = _make_multi_app(tmp_path)
    (proj_a / "runs").mkdir(exist_ok=True)
    client = TestClient(app)
    r = client.get("/projects/no-such-project/project-map")
    assert r.status_code == 404


# ── daemon isolation ──────────────────────────────────────────────────────────

def test_daemon_status_independent_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, proj_b = _make_multi_app(tmp_path)

    (proj_a / "runs").mkdir(exist_ok=True)
    (proj_b / "runs").mkdir(exist_ok=True)

    pid = os.getpid()
    (proj_a / "runs" / "daemon.pid").write_text(
        json.dumps({"pid": pid, "started_at": "2026-01-01T00:00:00Z"})
    )

    client = TestClient(app)
    r_a = client.get("/projects/project-a/daemon/status")
    r_b = client.get("/projects/project-b/daemon/status")

    assert r_a.status_code == 200
    assert r_a.json()["running"] is True
    assert r_b.status_code == 200
    assert r_b.json()["running"] is False


# ── tickets isolation ─────────────────────────────────────────────────────────

def test_tickets_isolated_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, proj_b = _make_multi_app(tmp_path)

    _make_ticket(proj_a, "T001", "PLAN_APPROVED")
    _make_ticket(proj_a, "T002", "RUNNING")
    (proj_b / "runs").mkdir(exist_ok=True)

    client = TestClient(app)
    r_a = client.get("/projects/project-a/tickets")
    r_b = client.get("/projects/project-b/tickets")

    assert r_a.status_code == 200
    ids_a = [t["ticket_id"] for t in r_a.json()]
    assert "T001" in ids_a
    assert "T002" in ids_a

    assert r_b.status_code == 200
    assert r_b.json() == []


def test_project_ticket_not_visible_in_other_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, proj_b = _make_multi_app(tmp_path)

    _make_ticket(proj_a, "T001", "PLAN_APPROVED")
    (proj_b / "runs").mkdir(exist_ok=True)

    client = TestClient(app)
    r = client.get("/projects/project-b/tickets/T001")
    assert r.status_code == 404


# ── runtime-status isolation ──────────────────────────────────────────────────

def test_runtime_status_independent_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, proj_b = _make_multi_app(tmp_path)

    _make_ticket(proj_a, "T001", "PLAN_APPROVED")
    (proj_b / "runs").mkdir(exist_ok=True)

    client = TestClient(app)
    r_a = client.get("/projects/project-a/daemon/runtime-status")
    r_b = client.get("/projects/project-b/daemon/runtime-status")

    assert r_a.status_code == 200
    assert r_b.status_code == 200
    queue_a = r_a.json()["intake_queue"]
    queue_b = r_b.json()["intake_queue"]
    assert any(e.get("title") == "T001" for e in queue_a)
    assert not any(e.get("title") == "T001" for e in queue_b)


# ── legacy routes still work ──────────────────────────────────────────────────

def test_legacy_daemon_status_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, _ = _make_multi_app(tmp_path)
    (proj_a / "runs").mkdir(exist_ok=True)
    client = TestClient(app)
    r = client.get("/daemon/status")
    assert r.status_code == 200
    assert "running" in r.json()


def test_legacy_tickets_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, proj_a, _ = _make_multi_app(tmp_path)
    _make_ticket(proj_a, "T001", "PLAN_APPROVED")
    client = TestClient(app)
    r = client.get("/tickets")
    assert r.status_code == 200
    ids = [t["ticket_id"] for t in r.json()]
    assert "T001" in ids
