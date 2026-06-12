"""Tests for auto_bootstrap() in project_bootstrap service."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_bootstrap import auto_bootstrap
from services.control_api.services.project_registry import ProjectRegistry


def _make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


def _make_git_worktree(path: Path, main_git_dir: Path) -> Path:
    """Create a worktree directory whose .git is a file pointing at main_git_dir."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").write_text(f"gitdir: {main_git_dir}\n", encoding="utf-8")
    return path


def _empty_registry(workspace_file: Path | None = None) -> ProjectRegistry:
    return ProjectRegistry(_entries=[], _workspace_file=workspace_file)


# ── runtime dirs ─────────────────────────────────────────────────────────────

def test_auto_bootstrap_creates_runtime_directories(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    project_runtime = runtime_root / "projects" / "ai-dev-factory"
    for subdir in ("runs", "logs", "state", "worktrees"):
        assert (project_runtime / subdir).is_dir(), f"missing {subdir}/"


def test_auto_bootstrap_writes_project_yml(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    yml = project_root / ".ai-dev-factory" / "project.yml"
    assert yml.exists()
    content = yml.read_text(encoding="utf-8")
    assert "name: ai-dev-factory" in content
    assert "bootstrapped_at:" in content


def test_auto_bootstrap_does_not_overwrite_existing_project_yml(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    ai_dir = project_root / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "project.yml").write_text("name: original\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    assert (ai_dir / "project.yml").read_text(encoding="utf-8") == "name: original\n"


# ── idempotency ───────────────────────────────────────────────────────────────

def test_auto_bootstrap_is_idempotent(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)
    # Second call must not raise.
    auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    assert registry.resolve("ai-dev-factory") == project_root.resolve()


# ── runtime_root=None ─────────────────────────────────────────────────────────

def test_auto_bootstrap_without_runtime_root_only_registers(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    registry = _empty_registry()

    auto_bootstrap(project_root, "ai-dev-factory", None, registry)

    assert registry.resolve("ai-dev-factory") == project_root.resolve()
    # No project.yml should be written.
    assert not (project_root / ".ai-dev-factory" / "project.yml").exists()


def test_auto_bootstrap_without_runtime_root_creates_no_dirs(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    registry = _empty_registry()

    auto_bootstrap(project_root, "ai-dev-factory", None, registry)

    assert not (tmp_path / "runtime").exists()


# ── invalid project ID ────────────────────────────────────────────────────────

def test_auto_bootstrap_invalid_id_logs_warning_and_returns(tmp_path, caplog):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    import logging
    with caplog.at_level(logging.WARNING, logger="control-api"):
        auto_bootstrap(project_root, "my/invalid-id", None, registry)

    assert any("invalid project_id" in r.message for r in caplog.records)
    assert registry.resolve("my/invalid-id") is None


# ── worktree (.git file) ──────────────────────────────────────────────────────

def test_auto_bootstrap_accepts_worktree_path(tmp_path):
    """auto_bootstrap must not reject a project root whose .git is a file."""
    main_clone = tmp_path / "ai-dev-factory"
    _make_git_repo(main_clone)

    # Create a fake worktree gitdir inside the main .git.
    worktree_gitdir = main_clone / ".git" / "worktrees" / "T186"
    worktree_gitdir.mkdir(parents=True)

    worktree_path = tmp_path / "worktrees" / "T186"
    _make_git_worktree(worktree_path, worktree_gitdir)

    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    # Should not raise even though .git is a file.
    auto_bootstrap(worktree_path, "ai-dev-factory", runtime_root, registry)

    assert registry.resolve("ai-dev-factory") is not None
