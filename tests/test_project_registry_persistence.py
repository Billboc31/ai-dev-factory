"""Tests for ProjectRegistry persistence (register, unregister, load_from_workspace_file)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_registry import ProjectRegistry


class _EmptyReader:
    def list_tickets(self, root):
        return []


# ── register ──────────────────────────────────────────────────────────────────

def test_register_adds_project(tmp_path):
    registry = ProjectRegistry(_entries=[])
    registry.register("my-project", tmp_path)
    assert registry.resolve("my-project") == tmp_path


def test_register_duplicate_raises(tmp_path):
    registry = ProjectRegistry(_entries=[])
    registry.register("my-project", tmp_path)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("my-project", tmp_path)


def test_register_persists_to_workspace_file(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    registry.register("my-project", tmp_path / "repo")

    assert workspace_file.exists()
    data = json.loads(workspace_file.read_text(encoding="utf-8"))
    assert "my-project" in data
    assert data["my-project"]["root"] == str(tmp_path / "repo")


# ── unregister ────────────────────────────────────────────────────────────────

def test_unregister_removes_project(tmp_path):
    registry = ProjectRegistry(_entries=[])
    registry.register("my-project", tmp_path)
    registry.unregister("my-project")
    assert registry.resolve("my-project") is None


def test_unregister_unknown_raises(tmp_path):
    registry = ProjectRegistry(_entries=[])
    with pytest.raises(ValueError, match="not registered"):
        registry.unregister("nonexistent")


def test_unregister_updates_workspace_file(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    registry.register("project-a", tmp_path / "a")
    registry.register("project-b", tmp_path / "b")
    registry.unregister("project-a")

    data = json.loads(workspace_file.read_text(encoding="utf-8"))
    assert "project-a" not in data
    assert "project-b" in data


# ── load_from_workspace_file ──────────────────────────────────────────────────

def test_load_from_workspace_file_rehydrates_projects(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    workspace_file.write_text(
        json.dumps({"my-project": {"root": str(tmp_path / "repo")}}),
        encoding="utf-8",
    )

    registry = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry.resolve("my-project") == tmp_path / "repo"


def test_load_from_workspace_file_returns_empty_when_absent(tmp_path):
    registry = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry.list_projects(_EmptyReader()) == []


def test_load_from_workspace_file_handles_corrupt_json(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    workspace_file.write_text("not valid json", encoding="utf-8")

    registry = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry.list_projects(_EmptyReader()) == []


def test_register_then_reload_roundtrip(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    registry1 = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    registry1.register("proj-a", tmp_path / "a")
    registry1.register("proj-b", tmp_path / "b")

    registry2 = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry2.resolve("proj-a") == tmp_path / "a"
    assert registry2.resolve("proj-b") == tmp_path / "b"


# ── project_runtime_root persistence ─────────────────────────────────────────

def test_register_persists_project_runtime_root(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    prt = tmp_path / "runtime" / "my-project"
    registry.register("my-project", tmp_path / "repo", project_runtime_root=prt)

    data = json.loads(workspace_file.read_text(encoding="utf-8"))
    assert data["my-project"]["project_runtime_root"] == str(prt)


def test_load_rehydrates_project_runtime_root(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    prt = tmp_path / "runtime" / "my-project"
    workspace_file.write_text(
        json.dumps({
            "my-project": {
                "root": str(tmp_path / "repo"),
                "project_runtime_root": str(prt),
            }
        }),
        encoding="utf-8",
    )

    registry = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry.resolve_runtime_root("my-project") == prt


def test_resolve_runtime_root_returns_none_when_absent(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    workspace_file.write_text(
        json.dumps({"my-project": {"root": str(tmp_path / "repo")}}),
        encoding="utf-8",
    )

    registry = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry.resolve_runtime_root("my-project") is None


def test_resolve_runtime_root_returns_none_for_unknown_project(tmp_path):
    registry = ProjectRegistry(_entries=[])
    assert registry.resolve_runtime_root("nonexistent") is None


def test_roundtrip_preserves_project_runtime_root(tmp_path):
    workspace_file = tmp_path / "workspace.json"
    prt = tmp_path / "runtime" / "my-project"

    registry1 = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    registry1.register("my-project", tmp_path / "repo", project_runtime_root=prt)

    registry2 = ProjectRegistry.load_from_workspace_file(tmp_path)
    assert registry2.resolve_runtime_root("my-project") == prt


def test_ensure_registered_preserves_existing_project_runtime_root(tmp_path):
    """Re-registration must not overwrite the existing project_runtime_root."""
    workspace_file = tmp_path / "workspace.json"
    prt_original = tmp_path / "runtime" / "my-project"
    prt_new = tmp_path / "other-runtime" / "my-project"

    registry = ProjectRegistry(_entries=[], _workspace_file=workspace_file)
    registry.ensure_registered("my-project", tmp_path / "repo", project_runtime_root=prt_original)

    # Re-register with a different runtime root — must be a no-op
    registry.ensure_registered("my-project", tmp_path / "repo", project_runtime_root=prt_new)

    assert registry.resolve_runtime_root("my-project") == prt_original
