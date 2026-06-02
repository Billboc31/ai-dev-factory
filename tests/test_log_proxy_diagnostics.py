"""Tests for _log_proxy_backend_diagnostics in run_sandbox."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.agent_runner.run_sandbox import _log_proxy_backend_diagnostics


def _make_inspect_result(returncode: int, payload: list | None) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = json.dumps(payload) if payload is not None else ""
    m.stderr = ""
    return m


def _container_inspect(
    *,
    status: str = "running",
    restarts: int = 0,
    health: str = "none",
    networks: list[str] | None = None,
) -> list[dict]:
    return [
        {
            "State": {
                "Status": status,
                "Health": {"Status": health} if health != "none" else {},
            },
            "RestartCount": restarts,
            "NetworkSettings": {
                "Networks": {n: {} for n in (networks or ["ai-dev-factory-runtime"])}
            },
        }
    ]


def _traefik_inspect(networks: list[str] | None = None) -> list[dict]:
    return [
        {
            "NetworkSettings": {
                "Networks": {n: {} for n in (networks or ["ai-dev-factory-runtime"])}
            }
        }
    ]


def _patch_imports(probe_return: dict | None = None):
    """Return a context manager stack that patches all service imports."""
    probe_return = probe_return if probe_return is not None else {"api": "reachable", "web": "reachable"}

    traefik_mock = MagicMock()
    traefik_mock.return_value.infra_container_id.return_value = "traefik-cid"

    probe_mock = MagicMock(return_value=probe_return)

    dns_mock = MagicMock(return_value={"api": "sandbox-abc123-api", "web": "sandbox-abc123-web"})
    urls_mock = MagicMock(return_value={
        "api": "http://sandbox-abc123-api:8080",
        "web": "http://sandbox-abc123-web:80",
    })

    return (
        patch("services.control_api.services.traefik_manager.TraefikManager", traefik_mock),
        patch("services.control_api.services.proxy_route_files.probe_backend_from_traefik_container", probe_mock),
        patch("services.control_api.services.proxy_network.sandbox_dns_aliases", dns_mock),
        patch("services.control_api.services.proxy_network.sandbox_backend_urls", urls_mock),
    )


def test_returned_dict_contains_required_keys(tmp_path):
    """Returned dict has backend_urls, aliases, traefik_probe, api_container, traefik_networks, failure_type."""
    log_path = tmp_path / "run.log"

    traefik_inspect = _make_inspect_result(0, _traefik_inspect())
    api_inspect = _make_inspect_result(0, _container_inspect())

    patches = _patch_imports()
    with patches[0], patches[1], patches[2], patches[3]:
        with patch("subprocess.run", side_effect=[traefik_inspect, api_inspect]):
            result = _log_proxy_backend_diagnostics("abc123", log_path)

    assert "backend_urls" in result
    assert "aliases" in result
    assert "traefik_probe" in result
    assert "traefik_networks" in result
    assert "api_container" in result
    assert "failure_type" in result

    api_c = result["api_container"]
    assert "name" in api_c
    assert "status" in api_c
    assert "restarts" in api_c
    assert "health" in api_c
    assert "networks" in api_c


def test_failure_type_crash_loop(tmp_path):
    """failure_type == 'crash_loop' when restarts > 0 and container exited."""
    log_path = tmp_path / "run.log"

    traefik_inspect = _make_inspect_result(0, _traefik_inspect())
    api_inspect = _make_inspect_result(0, _container_inspect(status="exited", restarts=3))

    patches = _patch_imports(probe_return={"api": "reachable", "web": "reachable"})
    with patches[0], patches[1], patches[2], patches[3]:
        with patch("subprocess.run", side_effect=[traefik_inspect, api_inspect]):
            result = _log_proxy_backend_diagnostics("abc123", log_path)

    assert result["failure_type"] == "crash_loop"


def test_failure_type_dns_network(tmp_path):
    """failure_type == 'dns_network' when Traefik probe fails and container is running."""
    log_path = tmp_path / "run.log"

    traefik_inspect = _make_inspect_result(0, _traefik_inspect())
    api_inspect = _make_inspect_result(0, _container_inspect(status="running", restarts=0))

    patches = _patch_imports(probe_return={"api": "failed: connection refused", "web": "failed: ..."})
    with patches[0], patches[1], patches[2], patches[3]:
        with patch("subprocess.run", side_effect=[traefik_inspect, api_inspect]):
            result = _log_proxy_backend_diagnostics("abc123", log_path)

    assert result["failure_type"] == "dns_network"


def test_traefik_networks_populated_when_inspect_succeeds(tmp_path):
    """traefik_networks contains the network names from docker inspect."""
    log_path = tmp_path / "run.log"

    traefik_inspect = _make_inspect_result(0, _traefik_inspect(networks=["ai-dev-factory-runtime", "bridge"]))
    api_inspect = _make_inspect_result(0, _container_inspect())

    patches = _patch_imports()
    with patches[0], patches[1], patches[2], patches[3]:
        with patch("subprocess.run", side_effect=[traefik_inspect, api_inspect]):
            result = _log_proxy_backend_diagnostics("abc123", log_path)

    assert "ai-dev-factory-runtime" in result["traefik_networks"]
    assert "bridge" in result["traefik_networks"]


def test_traefik_networks_empty_when_docker_unavailable(tmp_path):
    """traefik_networks is [] and no exception is raised when Docker is not on PATH."""
    log_path = tmp_path / "run.log"

    def raise_on_traefik(cmd, **_kw):
        if "traefik-cid" in cmd:
            raise FileNotFoundError("docker not found")
        return _make_inspect_result(0, _container_inspect())

    patches = _patch_imports()
    with patches[0], patches[1], patches[2], patches[3]:
        with patch("subprocess.run", side_effect=raise_on_traefik):
            result = _log_proxy_backend_diagnostics("abc123", log_path)

    assert result["traefik_networks"] == []
    assert "failure_type" in result
