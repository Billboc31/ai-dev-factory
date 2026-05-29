"""Tests for Traefik ↔ compose network attachment."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_manager import ProxyManager
from services.control_api.services.proxy_network import (
    attach_traefik_to_compose_project,
    compose_default_network_name,
    compose_service_backend_urls,
    detach_traefik_from_compose_project,
    resolve_route_backends,
)


def test_compose_default_network_name():
    assert compose_default_network_name("sandbox-abc123") == "sandbox-abc123_default"


def test_compose_service_backend_urls():
    urls = compose_service_backend_urls()
    assert urls["api"] == "http://api:8080"
    assert urls["web"] == "http://web:80"


def test_resolve_route_backends_uses_compose_when_attached():
    with patch(
        "services.control_api.services.proxy_network.attach_traefik_to_compose_project",
        return_value=True,
    ):
        backends, mode = resolve_route_backends(
            {"api": 8100, "web": 3100},
            "sandbox-env1",
        )
    assert mode == "compose"
    assert backends == compose_service_backend_urls()


def test_resolve_route_backends_falls_back_to_host_ports():
    with patch(
        "services.control_api.services.proxy_network.attach_traefik_to_compose_project",
        return_value=False,
    ):
        backends, mode = resolve_route_backends(
            {"api": 8100, "web": 3100},
            "sandbox-env1",
        )
    assert mode == "host"
    assert "host.docker.internal:8100" in backends["api"]
    assert "host.docker.internal:3100" in backends["web"]


def test_attach_traefik_connects_when_network_exists(tmp_path):
    logs: list[str] = []

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["docker", "inspect"]:
            return 0, json.dumps([{"NetworkSettings": {"Networks": {}}}]), ""
        if cmd[:3] == ["docker", "network", "inspect"]:
            return 0, "sandbox-abc_default", ""
        if cmd[:3] == ["docker", "network", "connect"]:
            return 0, "", ""
        return 0, "traefik-cid\n", ""

    with (
        patch(
            "services.control_api.services.proxy_network.traefik_container_id",
            return_value="traefik-cid-full",
        ),
        patch(
            "services.control_api.services.proxy_network.compose_network_exists",
            return_value=True,
        ),
        patch("services.control_api.services.proxy_network._run_docker", side_effect=fake_run),
    ):
        ok = attach_traefik_to_compose_project(
            "sandbox-abc",
            log=logs.append,
        )
    assert ok is True
    assert any("connected traefik" in line for line in logs)


def test_register_writes_compose_backend_urls(tmp_path):
    routes = tmp_path / "routes"
    with (
        patch(
            "services.control_api.services.proxy_network.attach_traefik_to_compose_project",
            return_value=True,
        ),
        patch(
            "services.control_api.services.proxy_manager.ensure_required_infra",
            return_value={"reverse_proxy": True},
        ),
    ):
        mgr = ProxyManager(routes_dir=routes, auto_ensure_infra=False)
        mgr.register(
            "env1",
            {"api": 8100, "web": 3100},
            compose_project="sandbox-env1",
            web_host="demo.localhost",
            api_host="api.demo.localhost",
        )
    content = (routes / "env1.yml").read_text(encoding="utf-8")
    assert 'url: "http://web:80"' in content
    assert 'url: "http://api:8080"' in content
    assert "host.docker.internal" not in content


def test_register_multiple_environments_compose_backends(tmp_path):
    routes = tmp_path / "routes"
    with patch(
        "services.control_api.services.proxy_network.attach_traefik_to_compose_project",
        return_value=True,
    ):
        mgr = ProxyManager(routes_dir=routes, auto_ensure_infra=False)
        mgr.register("a", {"api": 8080, "web": 3000}, compose_project="sandbox-a")
        mgr.register("b", {"api": 8180, "web": 3100}, compose_project="sandbox-b")
    a_yml = (routes / "a.yml").read_text(encoding="utf-8")
    b_yml = (routes / "b.yml").read_text(encoding="utf-8")
    assert "http://api:8080" in a_yml
    assert "http://api:8080" in b_yml
    assert "Host(`sandbox-a" in a_yml or "sandbox-a" in a_yml


def test_unregister_detaches_compose_network(tmp_path):
    routes = tmp_path / "routes"
    with patch(
        "services.control_api.services.proxy_manager.detach_traefik_from_compose_project",
    ) as mock_detach:
        mgr = ProxyManager(routes_dir=routes, auto_ensure_infra=False)
        (routes / "x.yml").write_text("http:\n  routers: {}\n", encoding="utf-8")
        mgr.unregister("x", compose_project="sandbox-x")
    mock_detach.assert_called_once_with("sandbox-x", log=None)
