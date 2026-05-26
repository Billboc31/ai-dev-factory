from __future__ import annotations

import logging
import os
from pathlib import Path

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


def _web_hostname(sandbox_id: str) -> str:
    return f"sandbox-{sandbox_id}.{_HOSTNAME_SUFFIX}"


def _api_hostname(sandbox_id: str) -> str:
    return f"api.sandbox-{sandbox_id}.{_HOSTNAME_SUFFIX}"


class ProxyManager:
    def __init__(self, routes_dir: Path | None = None) -> None:
        if routes_dir is None:
            runtime_root = Path(
                os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT", "~/runtime/ai-dev-factory")
            ).expanduser()
            routes_dir = runtime_root / "proxy" / "routes"
        self.routes_dir = routes_dir
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        dashboard_file = self.routes_dir / "_dashboard.yml"
        if not dashboard_file.exists():
            dashboard_file.write_text(_DASHBOARD_ROUTE, encoding="utf-8")

    def register(self, sandbox_id: str, ports: dict[str, int]) -> dict[str, str]:
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

        urls = {
            "web": f"http://{web_host}",
            "api": f"http://{api_host}",
        }
        logger.info("proxy route registered: sandbox=%s urls=%s", sandbox_id, urls)
        return urls

    def unregister(self, sandbox_id: str) -> None:
        route_file = self.routes_dir / f"{sandbox_id}.yml"
        try:
            route_file.unlink()
            logger.info("proxy route unregistered: sandbox=%s", sandbox_id)
        except FileNotFoundError:
            pass
