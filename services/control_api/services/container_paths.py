"""Map host runtime paths to their container-mounted equivalents.

The control API runs inside Docker, but project runtime roots persisted by the
host supervisor in ``workspace.json`` are absolute *host* paths (e.g.
``/Users/<you>/runtime/<project>``). Only ai-dev-factory's own runtime is
mounted at ``/runtime``; every managed project lives as a sibling under
``RUNTIME_BASE_ROOT`` and is bind-mounted under ``CONTAINER_RUNTIME_BASE``.

Without this mapping the container cannot read a managed project's
``runs/``, ``worktrees/``, ``state/`` or ``logs/`` — so filesystem-backed
endpoints (tickets list, logs, plan/review/diff) come back empty even though
the daemon is working and the Postgres-backed board shows the ticket.

On the host (supervisor, daemon, tests) ``AI_DEV_FACTORY_API_IN_DOCKER`` is
unset, so this is a strict no-op and paths are returned unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path


def _norm(value: str) -> str:
    return value.rstrip("/")


def _in_docker() -> bool:
    return os.environ.get("AI_DEV_FACTORY_API_IN_DOCKER", "").strip().lower() in ("1", "true", "yes")


def to_container_path(path: Path | str | None) -> Path | None:
    """Translate a host runtime path to the path visible inside the container.

    No-op when running on the host or when the path is already a container path
    (does not start with a known host runtime root).
    """
    if path is None:
        return None
    if not _in_docker():
        return Path(path)

    p = _norm(str(path))
    host_runtime = _norm(os.environ.get("HOST_RUNTIME_ROOT", ""))
    cont_runtime = _norm(os.environ.get("CONTAINER_RUNTIME_ROOT", "/runtime"))
    base = _norm(os.environ.get("RUNTIME_BASE_ROOT", ""))
    cont_base = _norm(os.environ.get("CONTAINER_RUNTIME_BASE", "/runtime-base"))

    # Most specific first: ai-dev-factory's own runtime root is a child of the
    # base, and is historically mounted at CONTAINER_RUNTIME_ROOT (/runtime).
    if host_runtime and (p == host_runtime or p.startswith(host_runtime + "/")):
        return Path(cont_runtime + p[len(host_runtime):])
    if base and (p == base or p.startswith(base + "/")):
        return Path(cont_base + p[len(base):])
    return Path(path)
