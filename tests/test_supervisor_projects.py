"""Tests for supervisor project host-filesystem endpoints (T188)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from services.supervisor.main import app
    return TestClient(app)


def _make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


def _make_git_worktree(path: Path, main_git_dir: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").write_text(f"gitdir: {main_git_dir}\n", encoding="utf-8")
    return path


# ── validate-path ─────────────────────────────────────────────────────────────

def test_validate_path_returns_resolved_path(tmp_path, client):
    repo = _make_git_repo(tmp_path / "my-project")
    resp = client.post("/projects/validate-path", json={"project_root": str(repo)})
    assert resp.status_code == 200
    data = resp.json()
    assert Path(data["resolved_path"]) == repo.resolve()
    assert data["is_dir"] is True
    assert data["is_git_repo"] is True
    assert data["git_root"] is not None


def test_validate_path_missing_path_returns_error(tmp_path, client):
    resp = client.post("/projects/validate-path", json={"project_root": str(tmp_path / "nonexistent")})
    assert resp.status_code == 422
    assert resp.json()["error"] == "path_not_found"


def test_validate_path_file_not_dir_returns_error(tmp_path, client):
    f = tmp_path / "some-file.txt"
    f.write_text("hello")
    resp = client.post("/projects/validate-path", json={"project_root": str(f)})
    assert resp.status_code == 422
    assert resp.json()["error"] == "not_a_directory"


def test_validate_path_non_git_dir_reports_is_git_repo_false(tmp_path, client):
    d = tmp_path / "not-a-repo"
    d.mkdir()
    resp = client.post("/projects/validate-path", json={"project_root": str(d)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_git_repo"] is False
    assert data["git_root"] is None


def test_validate_path_worktree_is_recognised_as_git(tmp_path, client):
    main_clone = tmp_path / "main"
    _make_git_repo(main_clone)
    worktree_gitdir = main_clone / ".git" / "worktrees" / "feat"
    worktree_gitdir.mkdir(parents=True)
    worktree = _make_git_worktree(tmp_path / "feat", worktree_gitdir)

    resp = client.post("/projects/validate-path", json={"project_root": str(worktree)})
    assert resp.status_code == 200
    assert resp.json()["is_git_repo"] is True


# ── bootstrap ─────────────────────────────────────────────────────────────────

def test_bootstrap_creates_runtime_directories(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    runtime_base_root = tmp_path / "runtime"
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(runtime_base_root))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert Path(data["runs_dir"]).is_dir()
    assert Path(data["logs_dir"]).is_dir()
    assert Path(data["state_dir"]).is_dir()
    assert Path(data["worktrees_dir"]).is_dir()


def test_bootstrap_creates_clones_directory(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    runtime_base_root = tmp_path / "runtime"
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(runtime_base_root))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 200
    assert (runtime_base_root / "my-project" / "clones").is_dir()


def test_bootstrap_writes_project_yml(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })

    yml = repo / ".ai-dev-factory" / "project.yml"
    assert yml.exists()
    content = yml.read_text(encoding="utf-8")
    assert "name: my-project" in content
    assert "bootstrapped_at:" in content


def test_bootstrap_does_not_overwrite_existing_project_yml(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    ai_dir = repo / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "project.yml").write_text("name: original\n", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })

    assert (ai_dir / "project.yml").read_text(encoding="utf-8") == "name: original\n"


def test_bootstrap_is_idempotent(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))
    payload = {
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    }

    r1 = client.post("/projects/bootstrap", json=payload)
    r2 = client.post("/projects/bootstrap", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_bootstrap_returns_correct_project_id(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.json()["project_id"] == "my-project"


def test_bootstrap_runtime_dirs_under_runtime_base_root(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "my-project")
    runtime_base_root = tmp_path / "runtime"
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(runtime_base_root))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    data = resp.json()
    # Dirs must be under <RUNTIME_BASE_ROOT>/<project_id>, NOT /projects/
    expected_prefix = str(runtime_base_root / "my-project")
    assert data["runs_dir"].startswith(expected_prefix)
    assert data["logs_dir"].startswith(expected_prefix)
    assert "projects" not in data["runs_dir"]


def test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base(tmp_path, client, monkeypatch):
    """When RUNTIME_BASE_ROOT is absent, derive it from parent of AI_DEV_FACTORY_RUNTIME_ROOT."""
    repo = _make_git_repo(tmp_path / "my-project")
    factory_runtime = tmp_path / "runtime" / "ai-dev-factory"
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(factory_runtime))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 200
    data = resp.json()
    # project_runtime_root must be <parent of factory_runtime>/<project_id>
    expected_prefix = str(tmp_path / "runtime" / "my-project")
    assert data["runs_dir"].startswith(expected_prefix)


def test_bootstrap_not_writable_runtime_base_returns_422(tmp_path, client, monkeypatch):
    """Unwritable runtime_base_root must return 422, not 500."""
    repo = _make_git_repo(tmp_path / "my-project")
    # Use /runtime as the base root — it is not writable on macOS/Linux
    monkeypatch.setenv("RUNTIME_BASE_ROOT", "/runtime")

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 422
    assert resp.json()["error"] == "runtime_base_root_not_writable"


def test_bootstrap_missing_path_returns_error(tmp_path, client, monkeypatch):
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))
    resp = client.post("/projects/bootstrap", json={
        "project_root": str(tmp_path / "nonexistent"),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 422
    assert resp.json()["error"] == "path_not_found"


def test_bootstrap_non_git_dir_returns_error(tmp_path, client, monkeypatch):
    d = tmp_path / "not-a-repo"
    d.mkdir()
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(d),
        "project_id": "my-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 422
    assert resp.json()["error"] == "git_not_found"


def test_bootstrap_detects_python_stack(tmp_path, client, monkeypatch):
    repo = _make_git_repo(tmp_path / "py-project")
    (repo / "pyproject.toml").write_text("[tool.poetry]\n", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(repo),
        "project_id": "py-project",
        "runtime_root": "ignored",
    })
    assert resp.json()["stack"] == "python"


def test_bootstrap_worktree_git_file_accepted(tmp_path, client, monkeypatch):
    main_clone = tmp_path / "main"
    _make_git_repo(main_clone)
    worktree_gitdir = main_clone / ".git" / "worktrees" / "feat"
    worktree_gitdir.mkdir(parents=True)
    worktree = _make_git_worktree(tmp_path / "feat", worktree_gitdir)
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "runtime"))

    resp = client.post("/projects/bootstrap", json={
        "project_root": str(worktree),
        "project_id": "feat-project",
        "runtime_root": "ignored",
    })
    assert resp.status_code == 200
