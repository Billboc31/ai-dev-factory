"""Unit tests for the project bootstrap service."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_bootstrap import bootstrap
from services.control_api.services.project_registry import ProjectRegistry


def _make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


class _EmptyReader:
    def list_tickets(self, root):
        return []


# ── bootstrap happy path ──────────────────────────────────────────────────────

def test_bootstrap_creates_runtime_directories(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    result = bootstrap(project_root, "my-project", runtime_root, registry)

    assert Path(result.runs_dir).is_dir()
    assert Path(result.logs_dir).is_dir()
    assert Path(result.state_dir).is_dir()
    assert Path(result.worktrees_dir).is_dir()


def test_bootstrap_runtime_dirs_are_under_project_runtime_root(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    result = bootstrap(project_root, "my-project", runtime_root, registry)

    expected_prefix = str(runtime_root / "projects" / "my-project")
    assert result.runs_dir.startswith(expected_prefix)
    assert result.logs_dir.startswith(expected_prefix)
    assert result.state_dir.startswith(expected_prefix)
    assert result.worktrees_dir.startswith(expected_prefix)


def test_bootstrap_writes_project_yml(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    bootstrap(project_root, "my-project", runtime_root, registry)

    yml = project_root / ".ai-dev-factory" / "project.yml"
    assert yml.exists()
    content = yml.read_text(encoding="utf-8")
    assert "name: my-project" in content
    assert "bootstrapped_at:" in content


def test_bootstrap_does_not_overwrite_existing_project_yml(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    ai_dir = project_root / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "project.yml").write_text("name: original\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    bootstrap(project_root, "my-project", runtime_root, registry)

    content = (ai_dir / "project.yml").read_text(encoding="utf-8")
    assert content == "name: original\n"


def test_bootstrap_registers_project(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    bootstrap(project_root, "my-project", runtime_root, registry)

    assert registry.resolve("my-project") == project_root.resolve()


def test_bootstrap_persists_workspace_json(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    workspace_file = runtime_root / "workspace.json"
    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)

    bootstrap(project_root, "my-project", runtime_root, registry)

    assert workspace_file.exists()
    data = json.loads(workspace_file.read_text(encoding="utf-8"))
    assert "my-project" in data


def test_bootstrap_returns_correct_project_id(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    result = bootstrap(project_root, "my-project", runtime_root, registry)

    assert result.project_id == "my-project"


# ── bootstrap error cases ─────────────────────────────────────────────────────

def test_bootstrap_raises_on_non_git_path(tmp_path):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    with pytest.raises(ValueError, match="not a git repository"):
        bootstrap(not_a_repo, "not-a-repo", runtime_root, registry)


def test_bootstrap_raises_on_invalid_project_id(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    with pytest.raises(ValueError):
        bootstrap(project_root, "my/invalid", runtime_root, registry)


def test_bootstrap_raises_on_duplicate_project_id(tmp_path):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    bootstrap(project_root, "my-project", runtime_root, registry)

    with pytest.raises(ValueError, match="already registered"):
        bootstrap(project_root, "my-project", runtime_root, registry)


# ── containment assertion in bootstrap ───────────────────────────────────────

def test_bootstrap_runtime_root_cannot_escape_projects_dir(tmp_path):
    """The bootstrap service must never produce a runtime root outside {runtime_root}/projects/."""
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = ProjectRegistry(_entries=[], _workspace_file=runtime_root / "workspace.json")

    result = bootstrap(project_root, "my-project", runtime_root, registry)

    # Runtime root must be nested inside {runtime_root}/projects/
    expected_prefix = str((runtime_root / "projects").resolve())
    assert result.runtime_root.startswith(expected_prefix)
