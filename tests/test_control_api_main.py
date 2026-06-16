"""Unit tests for control_api.create_app() — T192 runtime_base_root guard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import at module level so the module-level `app = create_app()` runs once
# during test collection (before any monkeypatch is active), leaving the module
# cached in sys.modules. Individual tests then call create_app() directly.
from services.control_api.main import create_app  # noqa: E402


@pytest.mark.parametrize("env_key,env_val", [
    ("AI_DEV_FACTORY_RUNTIME_ROOT", "/"),
    ("RUNTIME_BASE_ROOT", "/"),
])
def test_create_app_raises_when_runtime_base_root_resolves_to_filesystem_root(
    tmp_path, monkeypatch, env_key, env_val
):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.setenv(env_key, env_val)
    with pytest.raises(RuntimeError, match="filesystem root"):
        create_app(project_root=tmp_path)
