"""Pin the ai-dev-factory-runtime network declaration in docker-compose.traefik.yml.

Traefik must JOIN the pre-created network (external: true) rather than
owning it. When compose owns the network it silently recreates it on
``docker compose up``, which disconnects all backend containers and
produces 502s routed by Traefik but unreachable backends.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INFRA_COMPOSE = _REPO_ROOT / "deploy" / "infra" / "docker-compose.traefik.yml"


def test_traefik_runtime_network_is_external():
    data = yaml.safe_load(_INFRA_COMPOSE.read_text(encoding="utf-8"))
    net = data["networks"]["ai-dev-factory-runtime"]
    assert net.get("external") is True, (
        "ai-dev-factory-runtime must be 'external: true' so Traefik joins the"
        " network created by ensure_runtime_network() instead of recreating it"
    )


def test_traefik_runtime_network_has_no_driver():
    data = yaml.safe_load(_INFRA_COMPOSE.read_text(encoding="utf-8"))
    net = data["networks"]["ai-dev-factory-runtime"]
    assert "driver" not in net, (
        "ai-dev-factory-runtime must not contain a 'driver' key — compose must"
        " not manage this network"
    )


def test_traefik_runtime_network_has_no_name_override():
    data = yaml.safe_load(_INFRA_COMPOSE.read_text(encoding="utf-8"))
    net = data["networks"]["ai-dev-factory-runtime"]
    assert "name" not in net, (
        "ai-dev-factory-runtime must not contain a 'name' key — the network is"
        " owned by ensure_runtime_network(), not by compose"
    )
