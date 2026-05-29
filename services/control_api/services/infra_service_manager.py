"""Generic required-infrastructure orchestration for deploy flows.

Sandboxes (and future deploy modes) may depend on host-global infra
that is **not** part of the application ``docker-compose.yml`` —
reverse proxies, service meshes, etc. This module is the single place
that expresses *what* is required and *how* to ensure it, so callers
(``run_sandbox.py``, ``ProxyManager``, ``SandboxManager``) do not
scatter Traefik-specific lifecycle logic.

Current providers::

    kind            provider    ensure callable
    reverse_proxy   traefik     TraefikManager.ensure_running

Traefik is one implementation of the ``reverse_proxy`` kind. Adding
another provider later means registering a new
:class:`RequiredInfraService` — callers keep using
``ensure_required_infra()`` unchanged.

Route files for the reverse proxy always live under the **host**
runtime tree (``HOST_RUNTIME_ROOT/proxy/routes``), never under a
per-sandbox ``AI_DEV_FACTORY_RUNTIME_ROOT``. Traefik's file provider
mounts the host path — writing routes into a sandbox-scoped runtime
directory is a silent failure mode (routes exist, pretty URLs never
resolve).
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .runtime_resolver import get_sandbox_root
from .traefik_manager import TraefikManager

logger = logging.getLogger("control-api")

LogFn = Callable[[str], None]

# Relative path under ``HOST_RUNTIME_ROOT`` where Traefik's file
# provider watches dynamic routes. Must stay in sync with::
#
#     deploy/infra/docker-compose.traefik.yml
#       ${HOST_RUNTIME_ROOT}/proxy/routes:/routes
#
# and ``deploy/traefik/traefik.yml`` (directory: /routes inside the
# container). ``resolve_proxy_routes_dir()`` is the single resolver
# for the host-side absolute path.
PROXY_ROUTES_RELATIVE = Path("proxy") / "routes"
DEFAULT_HOST_RUNTIME_ROOT = Path("~/runtime/ai-dev-factory")


@dataclass(frozen=True)
class RequiredInfraService:
    """One host-global infra dependency."""

    name: str
    """Provider id (e.g. ``traefik``). Logged for operators."""

    kind: str
    """Logical role (e.g. ``reverse_proxy``). Callers filter on this."""

    ensure: Callable[[], bool]
    """Idempotent ensure hook. Must not raise — return False on failure."""


def _ensure_traefik_reverse_proxy() -> bool:
    try:
        return TraefikManager().ensure_running()
    except Exception as exc:  # defensive: docker missing, etc.
        logger.warning("infra: traefik ensure raised: %s", exc)
        return False


# Registry — extend here when new infra kinds are added.
_REQUIRED_INFRA: tuple[RequiredInfraService, ...] = (
    RequiredInfraService(
        name="traefik",
        kind="reverse_proxy",
        ensure=_ensure_traefik_reverse_proxy,
    ),
)


def required_infra_services(
    kinds: Iterable[str] | None = None,
) -> tuple[RequiredInfraService, ...]:
    """Return registered services, optionally filtered by *kinds*."""
    if kinds is None:
        return _REQUIRED_INFRA
    allowed = set(kinds)
    return tuple(s for s in _REQUIRED_INFRA if s.kind in allowed)


def resolve_host_runtime_root() -> Path:
    """Host-global runtime root — the tree Traefik and shared proxy
    routes use.

    Resolution order:

    1. ``HOST_RUNTIME_ROOT`` — canonical host path (set in
       ``deploy/.env`` for supervisor / workers).
    2. ``AI_DEV_FACTORY_RUNTIME_ROOT`` when it does **not** point
       inside a per-sandbox tree (main-runtime / dev fallback).
    3. Documented default ``~/runtime/ai-dev-factory``.
    """
    host = os.environ.get("HOST_RUNTIME_ROOT", "").strip()
    if host:
        return Path(host).expanduser().resolve()

    rr = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT", "").strip()
    if rr:
        p = Path(rr).expanduser().resolve()
        # Per-sandbox supervisors set RUNTIME_ROOT to a path under the
        # sandbox root — routes must NOT go there.
        if not p.is_relative_to(get_sandbox_root()):
            return p

    return DEFAULT_HOST_RUNTIME_ROOT.expanduser().resolve()


def resolve_proxy_routes_dir() -> Path:
    """Host-global directory watched by Traefik's file provider.

    Invariant (must hold in production)::

        resolve_proxy_routes_dir()
        == Path(HOST_RUNTIME_ROOT) / "proxy" / "routes"
        == host path mounted at /routes in the global Traefik container

    Never returns a path under per-sandbox
    ``…/sandboxes/<id>/runtime`` even when
    ``AI_DEV_FACTORY_RUNTIME_ROOT`` points there.
    """
    return resolve_host_runtime_root() / PROXY_ROUTES_RELATIVE


def log_infra_path_diagnostics(*, log: LogFn | None = None) -> tuple[Path, Path]:
    """Emit the host runtime + proxy routes paths before infra ensure.

    Makes mismatches between ``deploy/.env``, route registration, and
    the Traefik compose volume obvious in ``run.log`` / API logs.
    """
    host_root = resolve_host_runtime_root()
    routes_dir = resolve_proxy_routes_dir()
    for line in (
        f"infra: host runtime root = {host_root}",
        f"infra: proxy routes dir = {routes_dir}",
    ):
        if log is not None:
            log(line)
        else:
            logger.info(line)
    return host_root, routes_dir


def ensure_required_infra(
    *,
    kinds: Iterable[str] | None = None,
    log: LogFn | None = None,
) -> dict[str, bool]:
    """Ensure each required infra service is up.

    Returns ``{kind: ok}`` for every service attempted. Never raises.

    When *log* is provided (worker ``run.log``), messages use the
    ``infra:`` prefix requested by operators. Otherwise uses the
    module logger.
    """
    log_infra_path_diagnostics(log=log)

    results: dict[str, bool] = {}
    for svc in required_infra_services(kinds):
        line = f"infra: ensuring {svc.kind} (provider={svc.name})"
        if log is not None:
            log(line)
        else:
            logger.info(line)

        ok = svc.ensure()
        results[svc.kind] = ok

        if ok:
            ready = f"infra: {svc.kind} ready"
            if log is not None:
                log(ready)
            else:
                logger.info(ready)
        else:
            warn = (
                f"infra: {svc.kind} unavailable — pretty URLs may fail "
                f"(provider={svc.name})"
            )
            if log is not None:
                log(warn)
            else:
                logger.warning(warn)

    return results


def ensure_reverse_proxy(*, log: LogFn | None = None) -> bool:
    """Convenience wrapper for the common single-kind case."""
    return ensure_required_infra(kinds=["reverse_proxy"], log=log).get(
        "reverse_proxy", False
    )
