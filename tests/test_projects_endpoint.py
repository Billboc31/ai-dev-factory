"""Integration tests for GET /projects — single-root and multi-root modes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_app(tmp_path: Path, projects_root: Path | None = None):
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path, projects_root=projects_root)


def _make_ticket(root: Path, ticket_id: str, state: str) -> None:
    run_dir = root / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}-work"}),
        encoding="utf-8",
    )


def _make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


# ── single-root mode ──────────────────────────────────────────────────────────

def test_single_root_returns_one_project(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/projects")
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) == 1
    assert projects[0]["name"] == tmp_path.name


def test_single_root_tickets_count(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    _make_ticket(tmp_path, "T002", "DONE")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/projects")
    assert r.status_code == 200
    assert r.json()[0]["tickets_count"] == 2


# ── multi-root mode ───────────────────────────────────────────────────────────

def test_multi_root_returns_all_projects(tmp_path):
    pr = tmp_path / "projects"
    _make_git_repo(pr / "alpha")
    _make_git_repo(pr / "beta")

    client = TestClient(_make_app(tmp_path, projects_root=pr))
    r = client.get("/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "alpha" in names
    assert "beta" in names


def test_multi_root_tickets_count_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    pr = tmp_path / "projects"
    alpha = _make_git_repo(pr / "alpha")
    _make_ticket(alpha, "T001", "PLAN_APPROVED")
    _make_ticket(alpha, "T002", "DONE")
    _make_git_repo(pr / "beta")  # no tickets

    client = TestClient(_make_app(tmp_path, projects_root=pr))
    r = client.get("/projects")
    assert r.status_code == 200
    by_name = {p["name"]: p for p in r.json()}
    assert by_name["alpha"]["tickets_count"] == 2
    assert by_name["beta"]["tickets_count"] == 0


def test_multi_root_non_git_dirs_excluded(tmp_path):
    pr = tmp_path / "projects"
    _make_git_repo(pr / "real-project")
    (pr / "not-a-repo").mkdir(parents=True)  # no .git

    client = TestClient(_make_app(tmp_path, projects_root=pr))
    r = client.get("/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "real-project" in names
    assert "not-a-repo" not in names


# ── backward-compatibility regression ────────────────────────────────────────

def test_health_unaffected_single_root(tmp_path):
    client = TestClient(_make_app(tmp_path))
    assert client.get("/health").status_code == 200


def test_daemon_status_unaffected_single_root(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    assert client.get("/daemon/status").status_code == 200


def test_health_unaffected_multi_root(tmp_path):
    pr = tmp_path / "projects"
    _make_git_repo(pr / "proj-a")
    client = TestClient(_make_app(tmp_path, projects_root=pr))
    assert client.get("/health").status_code == 200


def test_daemon_status_unaffected_multi_root(tmp_path):
    pr = tmp_path / "projects"
    _make_git_repo(pr / "proj-a")
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path, projects_root=pr))
    assert client.get("/daemon/status").status_code == 200
