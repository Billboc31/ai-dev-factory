"""Tests for host→container runtime path mapping (multi-project visibility)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from control_api.services.container_paths import to_container_path


@pytest.fixture()
def docker_env(monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "1")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/Users/me/runtime/ai-dev-factory")
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", "/Users/me/runtime")
    monkeypatch.setenv("CONTAINER_RUNTIME_BASE", "/runtime-base")


def test_noop_on_host(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/Users/me/runtime/ai-dev-factory")
    monkeypatch.setenv("RUNTIME_BASE_ROOT", "/Users/me/runtime")
    p = "/Users/me/runtime/test-ai-dev"
    assert to_container_path(p) == Path(p)


def test_managed_project_host_path_maps_to_base(docker_env):
    # Sibling managed project under RUNTIME_BASE_ROOT.
    assert to_container_path("/Users/me/runtime/test-ai-dev") == Path("/runtime-base/test-ai-dev")
    assert to_container_path("/Users/me/runtime/test-ai-dev/worktrees/T000") == Path(
        "/runtime-base/test-ai-dev/worktrees/T000"
    )


def test_ai_dev_factory_host_runtime_maps_to_runtime(docker_env):
    # The most specific root wins: HOST_RUNTIME_ROOT → /runtime, not /runtime-base.
    assert to_container_path("/Users/me/runtime/ai-dev-factory") == Path("/runtime")
    assert to_container_path("/Users/me/runtime/ai-dev-factory/worktrees/T1") == Path(
        "/runtime/worktrees/T1"
    )


def test_already_container_path_unchanged(docker_env):
    # ai-dev-factory's registry already stores container paths.
    assert to_container_path("/runtime") == Path("/runtime")
    assert to_container_path("/runtime/clones/ai-dev-factory") == Path("/runtime/clones/ai-dev-factory")


def test_unrelated_path_unchanged(docker_env):
    # The human clone lives outside the runtime base — left as-is.
    assert to_container_path("/Users/me/test-ai-dev") == Path("/Users/me/test-ai-dev")


def test_none_returns_none(docker_env):
    assert to_container_path(None) is None
