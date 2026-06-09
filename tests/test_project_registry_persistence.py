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
