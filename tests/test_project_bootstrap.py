"""Unit tests for the project bootstrap service."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_bootstrap import bootstrap
from services.control_api.services.project_registry import ProjectRegistry

_MODULE = "services.control_api.services.project_bootstrap._call_supervisor"


def _registry(tmp_path: Path) -> ProjectRegistry:
    return ProjectRegistry(_entries=[], _workspace_file=tmp_path / "workspace.json")


def _mock_bootstrap_response(project_id: str, project_root: str, runtime_root: str) -> dict:
    base = f"{runtime_root}/projects/{project_id}"
    return {
        "project_id": project_id,
        "project_root": project_root,
        "runtime_root": base,
        "stack": "python",
        "runs_dir": f"{base}/runs",
        "logs_dir": f"{base}/logs",
        "state_dir": f"{base}/state",
        "worktrees_dir": f"{base}/worktrees",
    }


# ── happy path ────────────────────────────────────────────────────────────────

def test_bootstrap_returns_correct_project_id(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))

    with patch(_MODULE, return_value=(resp, None)):
        result = bootstrap(root, "my-project", runtime_root, _registry(tmp_path))

    assert result.project_id == "my-project"


def test_bootstrap_returns_paths_from_supervisor(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))

    with patch(_MODULE, return_value=(resp, None)):
        result = bootstrap(root, "my-project", runtime_root, _registry(tmp_path))

    expected_base = str(runtime_root / "projects" / "my-project")
    assert result.runs_dir == f"{expected_base}/runs"
    assert result.logs_dir == f"{expected_base}/logs"
    assert result.state_dir == f"{expected_base}/state"
    assert result.worktrees_dir == f"{expected_base}/worktrees"


def test_bootstrap_runtime_dirs_are_under_project_runtime_root(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))

    with patch(_MODULE, return_value=(resp, None)):
        result = bootstrap(root, "my-project", runtime_root, _registry(tmp_path))

    expected_prefix = str(runtime_root / "projects" / "my-project")
    assert result.runs_dir.startswith(expected_prefix)
    assert result.logs_dir.startswith(expected_prefix)
    assert result.state_dir.startswith(expected_prefix)
    assert result.worktrees_dir.startswith(expected_prefix)


def test_bootstrap_registers_project(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))
    registry = _registry(tmp_path)

    with patch(_MODULE, return_value=(resp, None)):
        bootstrap(root, "my-project", runtime_root, registry)

    assert registry.resolve("my-project") == Path(root)


def test_bootstrap_persists_workspace_json(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    workspace_file = tmp_path / "workspace.json"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))
    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)

    with patch(_MODULE, return_value=(resp, None)):
        bootstrap(root, "my-project", runtime_root, registry)

    assert workspace_file.exists()
    data = json.loads(workspace_file.read_text(encoding="utf-8"))
    assert "my-project" in data


def test_bootstrap_calls_supervisor_with_correct_args(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))

    with patch(_MODULE, return_value=(resp, None)) as mock_sv:
        bootstrap(root, "my-project", runtime_root, _registry(tmp_path))

    mock_sv.assert_called_once_with("POST", "/projects/bootstrap", {
        "project_root": root,
        "project_id": "my-project",
        "runtime_root": str(runtime_root),
    })


# ── error cases ───────────────────────────────────────────────────────────────

def test_bootstrap_raises_on_invalid_project_id(tmp_path):
    runtime_root = tmp_path / "runtime"
    with pytest.raises(ValueError):
        bootstrap(str(tmp_path / "my-project"), "my/invalid", runtime_root, _registry(tmp_path))


def test_bootstrap_raises_on_duplicate_project_id(tmp_path):
    root = str(tmp_path / "my-project")
    runtime_root = tmp_path / "runtime"
    resp = _mock_bootstrap_response("my-project", root, str(runtime_root))
    registry = _registry(tmp_path)

    with patch(_MODULE, return_value=(resp, None)):
        bootstrap(root, "my-project", runtime_root, registry)

    with patch(_MODULE, return_value=(resp, None)):
        with pytest.raises(ValueError, match="already registered"):
            bootstrap(root, "my-project", runtime_root, registry)


def test_bootstrap_raises_on_supervisor_unreachable(tmp_path):
    runtime_root = tmp_path / "runtime"
    with patch(_MODULE, return_value=(None, "supervisor_unreachable")):
        with pytest.raises(RuntimeError, match="supervisor unreachable"):
            bootstrap(str(tmp_path / "my-project"), "my-project", runtime_root, _registry(tmp_path))


def test_bootstrap_raises_on_non_git_path(tmp_path):
    runtime_root = tmp_path / "runtime"
    err_resp = {"error": "git_not_found", "detail": str(tmp_path / "my-project")}
    with patch(_MODULE, return_value=(err_resp, None)):
        with pytest.raises(ValueError, match="not a git repository"):
            bootstrap(str(tmp_path / "my-project"), "my-project", runtime_root, _registry(tmp_path))


def test_bootstrap_raises_on_path_not_found(tmp_path):
    runtime_root = tmp_path / "runtime"
    err_resp = {"error": "path_not_found", "detail": str(tmp_path / "missing")}
    with patch(_MODULE, return_value=(err_resp, None)):
        with pytest.raises(ValueError, match="path does not exist"):
            bootstrap(str(tmp_path / "missing"), "my-project", runtime_root, _registry(tmp_path))


# ── path-traversal guard ──────────────────────────────────────────────────────

def test_bootstrap_runtime_root_cannot_escape_projects_dir(tmp_path):
    """assert_contained() must reject project_ids that would escape the projects dir."""
    runtime_root = tmp_path / "runtime"
    with pytest.raises(ValueError):
        bootstrap(str(tmp_path / "my-project"), "..", runtime_root, _registry(tmp_path))
