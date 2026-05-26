"""Tests for generic required-infra orchestration."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services import infra_service_manager as ism
from services.control_api.services.infra_service_manager import (
    RequiredInfraService,
    ensure_required_infra,
    required_infra_services,
    resolve_host_runtime_root,
    resolve_proxy_routes_dir,
)


def test_required_infra_lists_reverse_proxy_traefik():
    kinds = {s.kind: s.name for s in required_infra_services()}
    assert kinds.get("reverse_proxy") == "traefik"


def test_required_infra_filter_by_kind():
    services = required_infra_services(kinds=["reverse_proxy"])
    assert len(services) == 1
    assert services[0].kind == "reverse_proxy"


def test_resolve_host_runtime_root_prefers_host_env(monkeypatch, tmp_path):
    host = tmp_path / "host-runtime"
    host.mkdir()
    sandbox = tmp_path / "sandboxes" / "abc" / "runtime"
    sandbox.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(sandbox))
    assert resolve_host_runtime_root() == host.resolve()


def test_resolve_host_runtime_root_skips_sandbox_scoped_runtime(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandboxes" / "abc" / "runtime"
    sandbox.mkdir(parents=True)
    monkeypatch.delenv("HOST_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(sandbox))
    root = resolve_host_runtime_root()
    assert "sandboxes" not in root.parts
    assert root == Path("~/runtime/ai-dev-factory").expanduser().resolve()


def test_resolve_proxy_routes_dir_under_host_runtime(monkeypatch, tmp_path):
    host = tmp_path / "host-runtime"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    assert resolve_proxy_routes_dir() == host / "proxy" / "routes"


def test_ensure_required_infra_logs_and_returns_results(monkeypatch):
    calls: list[str] = []
    logs: list[str] = []

    def fake_ensure() -> bool:
        calls.append("ensure")
        return True

    monkeypatch.setattr(
        ism,
        "_REQUIRED_INFRA",
        (
            RequiredInfraService(
                name="fake", kind="reverse_proxy", ensure=fake_ensure
            ),
        ),
    )
    results = ensure_required_infra(log=logs.append)
    assert results == {"reverse_proxy": True}
    assert calls == ["ensure"]
    assert any("infra: ensuring reverse_proxy" in line for line in logs)
    assert any("infra: reverse_proxy ready" in line for line in logs)


def test_ensure_required_infra_warns_when_unavailable(monkeypatch):
    logs: list[str] = []

    def fail_ensure() -> bool:
        return False

    monkeypatch.setattr(
        ism,
        "_REQUIRED_INFRA",
        (
            RequiredInfraService(
                name="fake", kind="reverse_proxy", ensure=fail_ensure
            ),
        ),
    )
    results = ensure_required_infra(log=logs.append)
    assert results["reverse_proxy"] is False
    assert any("pretty URLs may fail" in line for line in logs)


def test_ensure_reverse_proxy_delegates(monkeypatch):
    monkeypatch.setattr(
        ism, "ensure_required_infra", lambda **kw: {"reverse_proxy": True}
    )
    assert ism.ensure_reverse_proxy() is True
