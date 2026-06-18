"""Unit tests for control_api.create_app() — runtime_base_root resolution."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import at module level so the module-level `app = create_app()` runs once
# during test collection (before any monkeypatch is active), leaving the module
# cached in sys.modules. Individual tests then call create_app() directly.
from services.control_api.main import create_app  # noqa: E402


def test_create_app_raises_only_for_explicit_runtime_base_root_filesystem_root(
    tmp_path, monkeypatch
):
    """Only an explicit RUNTIME_BASE_ROOT=/ is rejected at startup."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("RUNTIME_BASE_ROOT", "/")
    with pytest.raises(RuntimeError, match="filesystem root"):
        create_app(project_root=tmp_path)


def test_create_app_starts_with_runtime_root_slash_runtime(tmp_path, monkeypatch):
    """AI_DEV_FACTORY_RUNTIME_ROOT=/runtime must NOT crash the API (Docker case)."""
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", "/runtime")
    app = create_app(project_root=tmp_path)
    # No multi-project base derived from a '/'-parent runtime root.
    assert app.state.runtime_base_root is None
    assert app.state.runtime_root == Path("/runtime")


def test_create_app_starts_without_runtime_base_root(tmp_path, monkeypatch):
    """Absence of RUNTIME_BASE_ROOT does not break startup (UI stays available)."""
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    app = create_app(project_root=tmp_path)
    assert app.state.runtime_base_root is None


def test_create_app_uses_explicit_runtime_base_root(tmp_path, monkeypatch):
    """A valid RUNTIME_BASE_ROOT is resolved and stored on app.state."""
    base = tmp_path / "multi-runtime"
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(base))
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    app = create_app(project_root=tmp_path)
    assert app.state.runtime_base_root == base.resolve()
