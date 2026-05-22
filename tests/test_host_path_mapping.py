"""Unit tests for ContainerToHostMapper."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from path_mapper import ContainerToHostMapper


def test_maps_container_path_to_host_path(monkeypatch):
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/app")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/Users/pierre/runtime/ai-dev-factory")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/runs/T100") == "/Users/pierre/runtime/ai-dev-factory/runs/T100"


def test_identity_when_env_vars_absent(monkeypatch):
    monkeypatch.delenv("CONTAINER_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("HOST_RUNTIME_ROOT", raising=False)
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/runs/T100") == "/app/runs/T100"


def test_path_inside_subdir_preserved(monkeypatch):
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/app")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/deep/nested/path/file.txt") == "/host/runtime/deep/nested/path/file.txt"


def test_unrelated_path_not_mutated(monkeypatch):
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/app")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/other/path/file.txt") == "/other/path/file.txt"


def test_ambiguous_prefix_not_mapped(monkeypatch):
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/app")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/applications/foo") == "/applications/foo"
