"""Shared runtime network and per-sandbox service discovery.

Every sandbox service joins ``ai-dev-factory-runtime`` via explicit aliases
declared in ``docker-compose.yml``. Traefik lives permanently on that same
network (``deploy/infra/docker-compose.traefik.yml``), so routes resolve
deterministically without any dynamic docker-network attach/detach.
"""
from __future__ import annotations

import re

RUNTIME_NETWORK_NAME = "ai-dev-factory-runtime"

_COMPOSE_API_PORT = 8080
_COMPOSE_WEB_PORT = 80

_DOCKER_SAFE_RE = re.compile(r"[^a-z0-9-]")


def _to_docker_safe_alias(sid: str) -> str:
    """Return a Docker DNS-safe slug from *sid*.

    Lowercases then strips any character outside ``[a-z0-9-]``.
    Docker alias resolution requires lowercase alphanumeric + hyphens only.
    """
    return _DOCKER_SAFE_RE.sub("", sid.lower())


def sandbox_dns_aliases(sandbox_id: str) -> dict[str, str]:
    """Return canonical DNS alias names used by sandbox services.

    These match the ``networks.aliases`` pattern in ``docker-compose.yml``
    after Docker normalises the alias to lowercase.
    """
    slug = _to_docker_safe_alias(sandbox_id)
    return {
        "api": f"sandbox-{slug}-api",
        "web": f"sandbox-{slug}-web",
    }


def sandbox_backend_urls(sandbox_id: str) -> dict[str, str]:
    """Traefik load-balancer target URLs using per-sandbox DNS aliases.

    Each sandbox service registers on ``ai-dev-factory-runtime`` with the
    aliases ``sandbox-<id>-api`` / ``sandbox-<id>-web``, making these names
    resolvable by Traefik without network mutation.

    The sandbox ID is normalised to a Docker-safe slug (lowercase,
    ``[a-z0-9-]`` only) so route file URLs always match the aliases
    Docker registers — even when the raw ID contains uppercase chars such
    as the ``T`` timestamp separator.
    """
    aliases = sandbox_dns_aliases(sandbox_id)
    return {
        "api": f"http://{aliases['api']}:{_COMPOSE_API_PORT}",
        "web": f"http://{aliases['web']}:{_COMPOSE_WEB_PORT}",
    }
