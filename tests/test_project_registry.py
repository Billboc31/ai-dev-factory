"""Unit tests for ProjectRegistry — project discovery and resolution logic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_registry import ProjectEntry, ProjectRegistry


class _FakeReader:
    """Stub artifact_reader that returns a pre-configured ticket list per root."""

    def __init__(self, tickets_by_root: dict[str, list]):
        self._map = tickets_by_root

    def list_tickets(self, root: Path):
        return self._map.get(str(root), [])


_empty_reader = _FakeReader({})


# ── from_single_root ──────────────────────────────────────────────────────────

def test_from_single_root_returns_one_project(tmp_path):
    registry = ProjectRegistry.from_single_root(tmp_path)
    projects = registry.list_projects(_empty_reader)
    assert len(projects) == 1


def test_from_single_root_correct_id_and_root(tmp_path):
    registry = ProjectRegistry.from_single_root(tmp_path)
    projects = registry.list_projects(_empty_reader)
    assert projects[0].name == tmp_path.name
    assert projects[0].root == str(tmp_path)


# ── projects_root scanning ────────────────────────────────────────────────────

def test_projects_root_discovers_git_subdirs(tmp_path):
    for name in ("project-a", "project-b"):
        d = tmp_path / name
        d.mkdir()
        (d / ".git").mkdir()

    registry = ProjectRegistry(projects_root=tmp_path)
    names = [p.name for p in registry.list_projects(_empty_reader)]
    assert "project-a" in names
    assert "project-b" in names


def test_non_git_dirs_are_ignored(tmp_path):
    (tmp_path / "not-a-repo").mkdir()

    registry = ProjectRegistry(projects_root=tmp_path)
    assert registry.list_projects(_empty_reader) == []


def test_empty_projects_root_returns_empty(tmp_path):
    registry = ProjectRegistry(projects_root=tmp_path)
    assert registry.list_projects(_empty_reader) == []


def test_git_file_entry_not_treated_as_repo(tmp_path):
    # git worktrees have a .git *file*, not a directory — must not be included
    d = tmp_path / "worktree-proj"
    d.mkdir()
    (d / ".git").write_text("gitdir: ../../.git/worktrees/foo")

    registry = ProjectRegistry(projects_root=tmp_path)
    assert registry.list_projects(_empty_reader) == []


# ── tickets_count ──────────────────────────────────────────────────────────────

def test_tickets_count_reflects_reader(tmp_path):
    d = tmp_path / "my-proj"
    d.mkdir()
    (d / ".git").mkdir()
    reader = _FakeReader({str(d): [object(), object(), object()]})

    registry = ProjectRegistry(projects_root=tmp_path)
    projects = registry.list_projects(reader)
    assert projects[0].tickets_count == 3


def test_tickets_count_zero_when_reader_raises(tmp_path):
    d = tmp_path / "bad-proj"
    d.mkdir()
    (d / ".git").mkdir()

    class _BrokenReader:
        def list_tickets(self, root):
            raise RuntimeError("disk error")

    registry = ProjectRegistry(projects_root=tmp_path)
    projects = registry.list_projects(_BrokenReader())
    assert projects[0].tickets_count == 0


# ── resolve ────────────────────────────────────────────────────────────────────

def test_resolve_known_id_returns_path(tmp_path):
    d = tmp_path / "known-proj"
    d.mkdir()
    (d / ".git").mkdir()

    registry = ProjectRegistry(projects_root=tmp_path)
    assert registry.resolve("known-proj") == d


def test_resolve_unknown_id_returns_none(tmp_path):
    registry = ProjectRegistry(projects_root=tmp_path)
    assert registry.resolve("nonexistent") is None
