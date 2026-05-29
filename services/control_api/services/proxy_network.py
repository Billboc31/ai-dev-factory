"""Shared runtime network and per-sandbox service discovery.

Every sandbox service joins ``ai-dev-factory-runtime`` via explicit aliases
declared in ``docker-compose.yml``. Traefik lives permanently on that same
network (``deploy/infra/docker-compose.traefik.yml``), so routes resolve
deterministically without any dynamic docker-network attach/detach.
"""
from __future__ import annotations

RUNTIME_NETWORK_NAME = "ai-dev-factory-runtime"

_COMPOSE_API_PORT = 8080
_COMPOSE_WEB_PORT = 80


def sandbox_backend_urls(sandbox_id: str) -> dict[str, str]:
    """Traefik load-balancer target URLs using per-sandbox DNS aliases.

    Each sandbox service registers on ``ai-dev-factory-runtime`` with the
    aliases ``sandbox-<id>-api`` / ``sandbox-<id>-web``, making these names
    resolvable by Traefik without network mutation.
    """
    return {
        "api": f"http://sandbox-{sandbox_id}-api:{_COMPOSE_API_PORT}",
        "web": f"http://sandbox-{sandbox_id}-web:{_COMPOSE_WEB_PORT}",
    }
