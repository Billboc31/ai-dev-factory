"""Tests for auto_bootstrap() in project_bootstrap service."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_bootstrap import auto_bootstrap
from services.control_api.services.project_registry import ProjectRegistry

_MODULE = "services.control_api.services.project_bootstrap._call_supervisor"


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


def _mock_response(project_id: str, project_root: Path, runtime_root: Path) -> dict:
    base = str(runtime_root / "projects" / project_id)
    return {
        "project_id": project_id,
        "project_root": str(project_root),
        "runtime_root": base,
        "stack": "unknown",
        "runs_dir": f"{base}/runs",
        "logs_dir": f"{base}/logs",
        "state_dir": f"{base}/state",
        "worktrees_dir": f"{base}/worktrees",
    }


# ── supervisor delegation ─────────────────────────────────────────────────────

def test_auto_bootstrap_calls_supervisor_when_runtime_root_given(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")
    resp = _mock_response("ai-dev-factory", project_root, runtime_root)

    with patch(_MODULE, return_value=(resp, None)) as mock_sv:
        auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    mock_sv.assert_called_once_with("POST", "/projects/bootstrap", {
        "project_root": str(project_root),
        "project_id": "ai-dev-factory",
        "runtime_root": str(runtime_root),
    })


def test_auto_bootstrap_registers_project(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")
    resp = _mock_response("ai-dev-factory", project_root, runtime_root)

    with patch(_MODULE, return_value=(resp, None)):
        auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    assert registry.resolve("ai-dev-factory") == project_root


# ── idempotency ───────────────────────────────────────────────────────────────

def test_auto_bootstrap_is_idempotent(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")
    resp = _mock_response("ai-dev-factory", project_root, runtime_root)

    with patch(_MODULE, return_value=(resp, None)):
        auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    with patch(_MODULE, return_value=(resp, None)):
        auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    assert registry.resolve("ai-dev-factory") == project_root


# ── runtime_root=None ─────────────────────────────────────────────────────────

def test_auto_bootstrap_without_runtime_root_only_registers(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    registry = _empty_registry()

    with patch(_MODULE) as mock_sv:
        auto_bootstrap(project_root, "ai-dev-factory", None, registry)

    mock_sv.assert_not_called()
    assert registry.resolve("ai-dev-factory") == project_root


def test_auto_bootstrap_without_runtime_root_creates_no_dirs(tmp_path):
    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    registry = _empty_registry()

    with patch(_MODULE):
        auto_bootstrap(project_root, "ai-dev-factory", None, registry)

    assert not (tmp_path / "runtime").exists()


# ── supervisor failure fallback ───────────────────────────────────────────────

def test_auto_bootstrap_supervisor_unreachable_still_registers(tmp_path, caplog):
    """When supervisor is down, auto_bootstrap logs a warning and still registers."""
    import logging

    project_root = _make_git_repo(tmp_path / "ai-dev-factory")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    with caplog.at_level(logging.WARNING, logger="control-api"):
        with patch(_MODULE, return_value=(None, "supervisor_unreachable")):
            auto_bootstrap(project_root, "ai-dev-factory", runtime_root, registry)

    assert any("supervisor" in r.message for r in caplog.records)
    assert registry.resolve("ai-dev-factory") == project_root


# ── invalid project ID ────────────────────────────────────────────────────────

def test_auto_bootstrap_invalid_id_logs_warning_and_returns(tmp_path, caplog):
    project_root = _make_git_repo(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")

    import logging
    with caplog.at_level(logging.WARNING, logger="control-api"):
        with patch(_MODULE):
            auto_bootstrap(project_root, "my/invalid-id", None, registry)

    assert any("invalid project_id" in r.message for r in caplog.records)
    assert registry.resolve("my/invalid-id") is None


# ── worktree (.git file) ──────────────────────────────────────────────────────

def test_auto_bootstrap_accepts_worktree_path(tmp_path):
    """auto_bootstrap must not reject a project root whose .git is a file."""
    main_clone = tmp_path / "ai-dev-factory"
    _make_git_repo(main_clone)

    worktree_gitdir = main_clone / ".git" / "worktrees" / "T186"
    worktree_gitdir.mkdir(parents=True)

    worktree_path = tmp_path / "worktrees" / "T186"
    _make_git_worktree(worktree_path, worktree_gitdir)

    runtime_root = tmp_path / "runtime"
    registry = _empty_registry(runtime_root / "workspace.json")
    resp = _mock_response("ai-dev-factory", worktree_path, runtime_root)

    with patch(_MODULE, return_value=(resp, None)):
        auto_bootstrap(worktree_path, "ai-dev-factory", runtime_root, registry)

    assert registry.resolve("ai-dev-factory") is not None
