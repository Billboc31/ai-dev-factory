"""Dynamic Traefik route registration for sandboxes.

Each sandbox gets two Host(...) routes:

  * ``sandbox-<id>.ai-dev-factory.localhost``           → web port
  * ``api.sandbox-<id>.ai-dev-factory.localhost``       → api port

Route files live under ``${HOST_RUNTIME_ROOT}/proxy/routes/<id>.yml``.
Traefik's file provider watches that directory (see
``deploy/infra/docker-compose.traefik.yml``).

Required host-global infra (reverse proxy) is ensured via
:mod:`infra_service_manager` before route files are written.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from .infra_service_manager import ensure_required_infra, resolve_proxy_routes_dir
from .proxy_network import sandbox_backend_urls
from .proxy_route_files import (
    atomic_write_route_file,
    cleanup_orphan_temp_files,
    route_file_path,
    safe_remove_route_file,
    validate_route_file,
    verify_route_visible_in_traefik_container,
)

logger = logging.getLogger("control-api")

_HOSTNAME_SUFFIX = "ai-dev-factory.localhost"

_DASHBOARD_ROUTE = """\
http:
  routers:
    traefik-dashboard:
      rule: "Host(`traefik.ai-dev-factory.localhost`)"
      service: api@internal
      entryPoints:
        - web
"""

# Filenames starting with ``_`` are infra-owned route files (the
# Traefik dashboard route, …) and MUST NOT be touched by sandbox
# cleanup. ``_dashboard.yml`` is the canonical example.
_INFRA_PREFIX = "_"


def _web_hostname(sandbox_id: str) -> str:
    return f"sandbox-{sandbox_id}.{_HOSTNAME_SUFFIX}"


def _api_hostname(sandbox_id: str) -> str:
    return f"api.sandbox-{sandbox_id}.{_HOSTNAME_SUFFIX}"


def build_sandbox_urls(
    sandbox_id: str,
    *,
    web_host: str | None = None,
    api_host: str | None = None,
) -> dict[str, str]:
    """Return the ``{web, api}`` pretty URLs for *sandbox_id*.

    Pure function — used by callers that need the URLs (sandbox env
    file writers, the host-side worker) without touching the proxy
    routes directory.

    If *web_host* / *api_host* are provided they are used verbatim;
    otherwise the default ``sandbox-<id>.*`` pattern is used.
    """
    wh = web_host or _web_hostname(sandbox_id)
    ah = api_host or _api_hostname(sandbox_id)
    return {"web": f"http://{wh}", "api": f"http://{ah}"}


class ProxyManager:
    def __init__(
        self,
        routes_dir: Path | None = None,
        *,
        auto_ensure_infra: bool = True,
        # Back-compat alias used by existing tests/callers.
        auto_start_traefik: bool | None = None,
    ) -> None:
        if routes_dir is None:
            routes_dir = resolve_proxy_routes_dir()
        self.routes_dir = routes_dir.resolve()
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        cleanup_orphan_temp_files(self.routes_dir)
        dashboard_file = self.routes_dir / "_dashboard.yml"
        if not dashboard_file.exists():
            atomic_write_route_file(dashboard_file, _DASHBOARD_ROUTE)
        # ``auto_ensure_infra=False`` keeps register() hermetic in tests.
        if auto_start_traefik is not None:
            auto_ensure_infra = auto_start_traefik
        self._auto_ensure_infra = auto_ensure_infra

    def register(
        self,
        sandbox_id: str,
        ports: dict[str, int] | None = None,
        *,
        web_host: str | None = None,
        api_host: str | None = None,
        log: Callable[[str], None] | None = None,
    ) -> dict[str, str]:
        if self._auto_ensure_infra:
            results = ensure_required_infra(kinds=["reverse_proxy"])
            if not results.get("reverse_proxy", False):
                logger.warning(
                    "proxy: reverse_proxy unavailable; route file will "
                    "be written to %s but pretty URLs may fail until infra "
                    "is up (run: bash deploy/infra/start_traefik.sh up)",
                    self.routes_dir,
                )

        wh = web_host or _web_hostname(sandbox_id)
        ah = api_host or _api_hostname(sandbox_id)
        backends = sandbox_backend_urls(sandbox_id)

        content = (
            f"http:\n"
            f"  routers:\n"
            f"    sandbox-{sandbox_id}-web:\n"
            f"      rule: \"Host(`{wh}`)\"\n"
            f"      service: sandbox-{sandbox_id}-web\n"
            f"      entryPoints:\n"
            f"        - web\n"
            f"    sandbox-{sandbox_id}-api:\n"
            f"      rule: \"Host(`{ah}`)\"\n"
            f"      service: sandbox-{sandbox_id}-api\n"
            f"      entryPoints:\n"
            f"        - web\n"
            f"  services:\n"
            f"    sandbox-{sandbox_id}-web:\n"
            f"      loadBalancer:\n"
            f"        servers:\n"
            f"          - url: \"{backends['web']}\"\n"
            f"    sandbox-{sandbox_id}-api:\n"
            f"      loadBalancer:\n"
            f"        servers:\n"
            f"          - url: \"{backends['api']}\"\n"
        )

        route_file = route_file_path(self.routes_dir, sandbox_id)
        atomic_write_route_file(route_file, content)

        err = validate_route_file(route_file)
        if err:
            raise RuntimeError(err)

        container_err = verify_route_visible_in_traefik_container(route_file)
        if container_err:
            if log:
                log(f"proxy: warning: {container_err}\n")
            logger.warning(container_err)
        elif log:
            log(
                f"proxy: route file verified on host and in Traefik container: "
                f"{route_file}\n"
            )

        urls = build_sandbox_urls(sandbox_id, web_host=web_host, api_host=api_host)
        logger.info(
            "proxy: route registered sandbox=%s dir=%s urls=%s file=%s",
            sandbox_id,
            self.routes_dir,
            urls,
            route_file,
        )
        return urls

    def unregister(
        self,
        sandbox_id: str,
        *,
        remove_route_file: bool = False,
        log: Callable[[str], None] | None = None,
    ) -> None:
        """Optionally remove the route file for *sandbox_id*.

        *remove_route_file* defaults to False so redeploy/healthcheck failures
        do not delete routes while Traefik's watcher may still reference them.
        Environment destruction passes ``remove_route_file=True``.
        """
        if remove_route_file:
            route_file = route_file_path(self.routes_dir, sandbox_id)
            safe_remove_route_file(route_file)
            logger.info("proxy route removed: sandbox=%s file=%s", sandbox_id, route_file)

    def cleanup_stale_routes(
        self, active_sandbox_ids: Iterable[str]
    ) -> list[str]:
        """Drop route files whose sandbox no longer exists.

        Called by ``SandboxManager.cleanup_stale_routes`` so that
        crashed/orphaned sandboxes don't leave stale subdomains
        pointing at recycled ports — a real risk after a hard
        crash where the supervisor wrote the route file but
        couldn't run the unregister path.

        ``_``-prefixed files are infra-owned and never removed.
        Returns the list of sandbox ids whose route files were
        deleted (useful for logging/assertions).
        """
        active = set(active_sandbox_ids)
        removed: list[str] = []
        for route_file in self.routes_dir.glob("*.yml"):
            name = route_file.stem
            if name.startswith(_INFRA_PREFIX):
                continue
            if name in active:
                continue
            safe_remove_route_file(route_file)
            removed.append(name)
        if removed:
            logger.info("proxy: cleaned %d stale route(s): %s", len(removed), removed)
        return removed
