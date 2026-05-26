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
from collections.abc import Iterable
from pathlib import Path

from .infra_service_manager import ensure_required_infra, resolve_proxy_routes_dir

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


def build_sandbox_urls(sandbox_id: str) -> dict[str, str]:
    """Return the ``{web, api}`` pretty URLs for *sandbox_id*.

    Pure function — used by callers that need the URLs (sandbox env
    file writers, the host-side worker) without touching the proxy
    routes directory.
    """
    return {
        "web": f"http://{_web_hostname(sandbox_id)}",
        "api": f"http://{_api_hostname(sandbox_id)}",
    }


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
        self.routes_dir = routes_dir
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        dashboard_file = self.routes_dir / "_dashboard.yml"
        if not dashboard_file.exists():
            dashboard_file.write_text(_DASHBOARD_ROUTE, encoding="utf-8")
        # ``auto_ensure_infra=False`` keeps register() hermetic in tests.
        if auto_start_traefik is not None:
            auto_ensure_infra = auto_start_traefik
        self._auto_ensure_infra = auto_ensure_infra

    def register(self, sandbox_id: str, ports: dict[str, int]) -> dict[str, str]:
        if self._auto_ensure_infra:
            results = ensure_required_infra(kinds=["reverse_proxy"])
            if not results.get("reverse_proxy", False):
                logger.warning(
                    "proxy: reverse_proxy unavailable; route file will "
                    "be written to %s but pretty URLs may fail until infra "
                    "is up (run: bash deploy/infra/start_traefik.sh up)",
                    self.routes_dir,
                )

        web_host = _web_hostname(sandbox_id)
        api_host = _api_hostname(sandbox_id)
        web_port = ports.get("web", 3000)
        api_port = ports.get("api", 8080)

        content = (
            f"http:\n"
            f"  routers:\n"
            f"    sandbox-{sandbox_id}-web:\n"
            f"      rule: \"Host(`{web_host}`)\"\n"
            f"      service: sandbox-{sandbox_id}-web\n"
            f"      entryPoints:\n"
            f"        - web\n"
            f"    sandbox-{sandbox_id}-api:\n"
            f"      rule: \"Host(`{api_host}`)\"\n"
            f"      service: sandbox-{sandbox_id}-api\n"
            f"      entryPoints:\n"
            f"        - web\n"
            f"  services:\n"
            f"    sandbox-{sandbox_id}-web:\n"
            f"      loadBalancer:\n"
            f"        servers:\n"
            f"          - url: \"http://host.docker.internal:{web_port}\"\n"
            f"    sandbox-{sandbox_id}-api:\n"
            f"      loadBalancer:\n"
            f"        servers:\n"
            f"          - url: \"http://host.docker.internal:{api_port}\"\n"
        )

        route_file = self.routes_dir / f"{sandbox_id}.yml"
        tmp_file = route_file.with_suffix(".yml.tmp")
        tmp_file.write_text(content, encoding="utf-8")
        tmp_file.rename(route_file)

        urls = build_sandbox_urls(sandbox_id)
        logger.info(
            "proxy: route registered sandbox=%s dir=%s urls=%s",
            sandbox_id,
            self.routes_dir,
            urls,
        )
        return urls

    def unregister(self, sandbox_id: str) -> None:
        """Remove the route file for *sandbox_id*. No-op if missing.

        Never touches the global Traefik infrastructure (the
        ``_dashboard.yml`` file or any other ``_``-prefixed file) and
        never touches other sandboxes' routes.
        """
        route_file = self.routes_dir / f"{sandbox_id}.yml"
        try:
            route_file.unlink()
            logger.info("proxy route unregistered: sandbox=%s", sandbox_id)
        except FileNotFoundError:
            pass

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
            try:
                route_file.unlink()
                removed.append(name)
            except OSError as exc:
                logger.warning(
                    "proxy: failed to remove stale route %s: %s",
                    route_file, exc,
                )
        if removed:
            logger.info("proxy: cleaned %d stale route(s): %s", len(removed), removed)
        return removed
