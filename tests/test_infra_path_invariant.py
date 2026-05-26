"""Cross-component tests for HOST_RUNTIME_ROOT/proxy/routes invariant.

The global Traefik container, ProxyManager, and sandbox workers must
all agree on the host path where dynamic route files are written.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.infra_service_manager import (
    PROXY_ROUTES_RELATIVE,
    log_infra_path_diagnostics,
    resolve_host_runtime_root,
    resolve_proxy_routes_dir,
)
from services.control_api.services.proxy_manager import ProxyManager
from services.control_api.services.sandbox_manager import SandboxManager

_REPO = Path(__file__).resolve().parents[1]
_TRAEFIK_COMPOSE = _REPO / "deploy" / "infra" / "docker-compose.traefik.yml"
_TRAEFIK_CONFIG = _REPO / "deploy" / "traefik" / "traefik.yml"


def test_traefik_compose_mount_uses_host_runtime_proxy_routes():
    """Volume spec must reference HOST_RUNTIME_ROOT/proxy/routes."""
    text = _TRAEFIK_COMPOSE.read_text(encoding="utf-8")
    assert re.search(
        r"\$\{HOST_RUNTIME_ROOT[^}]*\}/proxy/routes\s*:\s*/routes",
        text,
    ), (
        "deploy/infra/docker-compose.traefik.yml must mount "
        "${HOST_RUNTIME_ROOT}/proxy/routes at /routes"
    )


def test_traefik_static_config_watches_routes_directory():
    text = _TRAEFIK_CONFIG.read_text(encoding="utf-8")
    assert re.search(r"directory:\s*/routes", text), (
        "deploy/traefik/traefik.yml file provider must watch /routes"
    )


def test_resolve_proxy_routes_dir_uses_host_runtime_root(monkeypatch, tmp_path):
    host = tmp_path / "my-host-runtime"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    monkeypatch.setenv(
        "AI_DEV_FACTORY_RUNTIME_ROOT",
        str(tmp_path / "sandboxes" / "abc" / "runtime"),
    )
    assert resolve_proxy_routes_dir() == host / PROXY_ROUTES_RELATIVE


def test_resolve_proxy_routes_dir_ignores_sandbox_runtime_without_host_env(
    monkeypatch, tmp_path,
):
    sandbox = tmp_path / "sandboxes" / "x" / "runtime"
    sandbox.mkdir(parents=True)
    monkeypatch.delenv("HOST_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(sandbox))
    routes = resolve_proxy_routes_dir()
    assert "sandboxes" not in routes.parts
    assert routes.name == "routes"
    assert routes.parent.name == "proxy"


def test_proxy_manager_default_routes_dir_equals_resolver(monkeypatch, tmp_path):
    host = tmp_path / "host"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    pm = ProxyManager(auto_ensure_infra=False)
    assert pm.routes_dir.resolve() == resolve_proxy_routes_dir().resolve()


def test_sandbox_manager_proxy_uses_host_global_routes_dir(
    monkeypatch, tmp_path,
):
    host = tmp_path / "host-global"
    host.mkdir()
    sandbox_rt = tmp_path / "sandboxes" / "id1" / "runtime"
    sandbox_rt.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(sandbox_rt))

    mgr = SandboxManager(sandboxes_dir=tmp_path / "sandboxes")
    mgr._proxy._auto_ensure_infra = False
    expected = host / "proxy" / "routes"
    assert mgr._proxy.routes_dir.resolve() == expected.resolve()


def test_sandbox_manager_start_registers_under_host_routes_dir(
    monkeypatch, tmp_path,
):
    host = tmp_path / "host-global"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))

    mgr = SandboxManager(sandboxes_dir=tmp_path / "sandboxes")
    mgr._proxy._auto_ensure_infra = False

    state = mgr.create("T001", "/project")
    with patch.object(mgr, "_start_sandbox_supervisor", return_value=123):
        with patch.object(mgr, "_run_compose", return_value=(0, "", "")):
            state = mgr.start(state.id)

    route_file = host / "proxy" / "routes" / f"{state.id}.yml"
    assert route_file.exists(), (
        f"dashboard start must write {route_file}, not under sandbox runtime"
    )


def test_log_infra_path_diagnostics_emits_expected_lines(monkeypatch, tmp_path):
    host = tmp_path / "host"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    logs: list[str] = []
    root, routes = log_infra_path_diagnostics(log=logs.append)
    assert root == host.resolve()
    assert routes == host / "proxy" / "routes"
    assert any("infra: host runtime root =" in line for line in logs)
    assert any("infra: proxy routes dir =" in line for line in logs)
    assert str(host) in logs[0]
    assert str(routes) in logs[1]


def test_ensure_required_infra_logs_path_diagnostics_first(monkeypatch, tmp_path):
    import services.control_api.services.infra_service_manager as ism
    from services.control_api.services.infra_service_manager import (
        RequiredInfraService,
        ensure_required_infra,
    )

    host = tmp_path / "host"
    host.mkdir()
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    logs: list[str] = []

    monkeypatch.setattr(
        ism,
        "_REQUIRED_INFRA",
        (
            RequiredInfraService(
                name="fake", kind="reverse_proxy", ensure=lambda: True
            ),
        ),
    )
    ensure_required_infra(log=logs.append)
    assert logs[0].startswith("infra: host runtime root =")
    assert logs[1].startswith("infra: proxy routes dir =")
    assert "infra: ensuring reverse_proxy" in logs[2]
