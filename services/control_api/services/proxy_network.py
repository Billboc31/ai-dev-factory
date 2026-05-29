"""Attach the global Traefik container to per-environment Compose networks.

Sandboxes/environments run ``docker compose -p <project> up`` on an isolated
project network (``<project>_default``). Traefik lives on ``ai-dev-factory-infra``
and must join each environment network so routes can target ``http://api:8080``
and ``http://web:80`` instead of relying on ``host.docker.internal`` port
forwarding (which breaks when Traefik and app stacks are on different networks).
"""
from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from .traefik_manager import INFRA_PROJECT_NAME, INFRA_SERVICE_NAME, TraefikManager

logger = logging.getLogger("control-api")

# Internal container ports from the project docker-compose.yml (not host mappings).
_COMPOSE_API_PORT = 8080
_COMPOSE_WEB_PORT = 80


def compose_default_network_name(compose_project: str) -> str:
    """Default bridge network Docker Compose creates for *compose_project*."""
    return f"{compose_project}_default"


def compose_service_backend_urls() -> dict[str, str]:
    """Load-balancer target URLs when Traefik shares the compose network."""
    return {
        "web": f"http://web:{_COMPOSE_WEB_PORT}",
        "api": f"http://api:{_COMPOSE_API_PORT}",
    }


def host_port_backend_urls(ports: dict[str, int]) -> dict[str, str]:
    """Fallback targets via host-published ports (legacy behaviour)."""
    return {
        "web": f"http://host.docker.internal:{ports.get('web', 3000)}",
        "api": f"http://host.docker.internal:{ports.get('api', 8080)}",
    }


def _run_docker(cmd: list[str], *, timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def traefik_container_id() -> str | None:
    return TraefikManager().infra_container_id()


def traefik_attached_networks(container_id: str) -> set[str]:
    rc, out, _err = _run_docker(["docker", "inspect", container_id])
    if rc != 0 or not out.strip():
        return set()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return set()
    if not data or not isinstance(data[0], dict):
        return set()
    networks = data[0].get("NetworkSettings", {}).get("Networks", {})
    if not isinstance(networks, dict):
        return set()
    return set(networks.keys())


def compose_network_exists(network_name: str) -> bool:
    rc, out, _err = _run_docker(
        ["docker", "network", "inspect", network_name, "--format", "{{.Name}}"]
    )
    return rc == 0 and out.strip() == network_name


def attach_traefik_to_compose_project(
    compose_project: str,
    *,
    log: Callable[[str], None] | None = None,
) -> bool:
    """Connect the infra Traefik container to *compose_project*'s network."""
    network = compose_default_network_name(compose_project)
    cid = traefik_container_id()
    if not cid:
        msg = (
            f"proxy-network: traefik container not running "
            f"(project={INFRA_PROJECT_NAME} service={INFRA_SERVICE_NAME})"
        )
        logger.warning(msg)
        if log:
            log(f"{msg}\n")
        return False
    if network in traefik_attached_networks(cid):
        if log:
            log(f"proxy-network: traefik already on {network}\n")
        return True
    if not compose_network_exists(network):
        msg = f"proxy-network: compose network {network!r} does not exist yet"
        logger.warning(msg)
        if log:
            log(f"{msg}\n")
        return False
    rc, _out, err = _run_docker(["docker", "network", "connect", network, cid])
    if rc != 0:
        already = "already exists" in err.lower() or "is already attached" in err.lower()
        if already:
            if log:
                log(f"proxy-network: traefik already connected to {network}\n")
            return True
        msg = f"proxy-network: connect traefik to {network} failed: {err.strip()}"
        logger.warning(msg)
        if log:
            log(f"{msg}\n")
        return False
    if log:
        log(
            f"proxy-network: connected traefik ({cid[:12]}) to {network} "
            f"(compose_project={compose_project})\n"
        )
    logger.info(
        "proxy-network: traefik attached sandbox_network=%s compose_project=%s",
        network,
        compose_project,
    )
    return True


def detach_traefik_from_compose_project(
    compose_project: str,
    *,
    log: Callable[[str], None] | None = None,
) -> bool:
    """Disconnect Traefik from an environment network on teardown."""
    network = compose_default_network_name(compose_project)
    cid = traefik_container_id()
    if not cid:
        return False
    if network not in traefik_attached_networks(cid):
        return True
    rc, _out, err = _run_docker(["docker", "network", "disconnect", network, cid])
    if rc != 0:
        msg = f"proxy-network: disconnect traefik from {network} failed: {err.strip()}"
        logger.warning(msg)
        if log:
            log(f"{msg}\n")
        return False
    if log:
        log(f"proxy-network: disconnected traefik from {network}\n")
    return True


def resolve_route_backends(
    ports: dict[str, int],
    compose_project: str | None,
    *,
    log: Callable[[str], None] | None = None,
) -> tuple[dict[str, str], str]:
    """Pick compose-service or host-port backends; attach Traefik when possible."""
    if compose_project:
        if attach_traefik_to_compose_project(compose_project, log=log):
            return compose_service_backend_urls(), "compose"
        if log:
            log(
                "proxy-network: falling back to host.docker.internal backends "
                f"for compose_project={compose_project}\n"
            )
    return host_port_backend_urls(ports), "host"
