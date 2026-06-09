"""Unit tests for project_id helpers: normalize, validate, assert_contained."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_id import (
    assert_contained,
    normalize_project_id,
    validate_project_id,
)


# ── normalize_project_id ──────────────────────────────────────────────────────

def test_normalize_lowercases():
    assert normalize_project_id("MyProject") == "myproject"


def test_normalize_collapses_unsupported_chars():
    assert normalize_project_id("my project!") == "my-project"


def test_normalize_strips_trailing_dash():
    result = normalize_project_id("my-project!")
    assert not result.endswith("-")


def test_normalize_truncates_to_64():
    long_name = "a" * 100
    assert len(normalize_project_id(long_name)) == 64


def test_normalize_raises_on_empty():
    with pytest.raises(ValueError):
        normalize_project_id("")


def test_normalize_raises_on_whitespace_only():
    with pytest.raises(ValueError):
        normalize_project_id("   ")


def test_normalize_path_basename():
    result = normalize_project_id("/home/user/my-cool-project")
    assert "my-cool-project" in result or result == "home-user-my-cool-project"


# ── validate_project_id ───────────────────────────────────────────────────────

def test_validate_accepts_valid_ids():
    for pid in ("my-project", "my_project", "project1", "a", "a1b2c3"):
        assert validate_project_id(pid) == pid


def test_validate_rejects_empty():
    with pytest.raises(ValueError):
        validate_project_id("")


def test_validate_rejects_whitespace_only():
    with pytest.raises(ValueError):
        validate_project_id("   ")


def test_validate_rejects_leading_whitespace():
    with pytest.raises(ValueError):
        validate_project_id(" myproject")


def test_validate_rejects_slash():
    with pytest.raises(ValueError):
        validate_project_id("my/project")


def test_validate_rejects_backslash():
    with pytest.raises(ValueError):
        validate_project_id("my\\project")


def test_validate_rejects_dot_dot():
    with pytest.raises(ValueError):
        validate_project_id("..")


def test_validate_rejects_dot():
    with pytest.raises(ValueError):
        validate_project_id(".")


def test_validate_rejects_embedded_dot_dot():
    with pytest.raises(ValueError):
        validate_project_id("foo..bar")


def test_validate_rejects_uppercase():
    with pytest.raises(ValueError):
        validate_project_id("MyProject")


def test_validate_rejects_starts_with_dash():
    with pytest.raises(ValueError):
        validate_project_id("-myproject")


def test_validate_rejects_ends_with_dash():
    with pytest.raises(ValueError):
        validate_project_id("myproject-")


def test_validate_rejects_too_long():
    with pytest.raises(ValueError):
        validate_project_id("a" * 65)


# ── assert_contained ─────────────────────────────────────────────────────────

def test_assert_contained_returns_correct_path(tmp_path):
    result = assert_contained(tmp_path, "my-project")
    assert result == (tmp_path / "projects" / "my-project").resolve()


def test_assert_contained_raises_on_invalid_id(tmp_path):
    with pytest.raises(ValueError):
        assert_contained(tmp_path, "my/project")


def test_assert_contained_prevents_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        assert_contained(tmp_path, "..")


def test_assert_contained_different_ids_produce_different_paths(tmp_path):
    p1 = assert_contained(tmp_path, "project-a")
    p2 = assert_contained(tmp_path, "project-b")
    assert p1 != p2
    assert str(p1).startswith(str(tmp_path / "projects"))
    assert str(p2).startswith(str(tmp_path / "projects"))
