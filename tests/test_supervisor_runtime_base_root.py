"""Unit tests for supervisor._runtime_base_root() — T192 regression coverage."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from services.supervisor.main import _runtime_base_root


@pytest.mark.parametrize("env_key,env_val", [
    ("RUNTIME_BASE_ROOT", "/"),
    ("AI_DEV_FACTORY_RUNTIME_ROOT", "/"),
])
def test_runtime_base_root_raises_on_filesystem_root(env_key, env_val, monkeypatch):
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv(env_key, env_val)
    with pytest.raises(RuntimeError, match="filesystem root"):
        _runtime_base_root()


def test_runtime_base_root_valid_runtime_base_root(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(tmp_path / "my-runtime"))
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    result = _runtime_base_root()
    assert result == (tmp_path / "my-runtime").resolve()


def test_runtime_base_root_no_env(monkeypatch):
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    result = _runtime_base_root()
    assert result == Path.home() / "runtime"


def test_runtime_base_root_derives_from_factory_root(tmp_path, monkeypatch):
    factory_runtime = tmp_path / "runtime" / "ai-dev-factory"
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(factory_runtime))
    result = _runtime_base_root()
    assert result == tmp_path / "runtime"
