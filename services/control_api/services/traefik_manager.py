"""Idempotent auto-start manager for the global Traefik reverse proxy.

The reverse proxy lives in ``deploy/infra/docker-compose.traefik.yml``
under the dedicated compose project ``ai-dev-factory-infra``. It is
**single-instance per host** — sandbox compose runs must never spawn
their own Traefik (that would conflict on port 80).

Readiness invariant (all must hold)::

    1. Infra compose ``traefik`` service is running.
    2. That **same** container publishes host port 80 (not merely
       ``80/tcp`` exposed internally while another container owns
       ``0.0.0.0:80``).
    3. Its ``/routes`` bind mount matches ``resolve_proxy_routes_dir()``.

A common failure mode on dev machines::

    ai-dev-factory-infra-traefik-1   Up   80/tcp
    ai-dev-factory-traefik-1         Up   0.0.0.0:80->80/tcp

Here ``is_listening()`` and ``is_running()`` can both be true while
pretty URLs still 404 — the old Traefik answers on port 80 but does
not watch new route files under ``HOST_RUNTIME_ROOT/proxy/routes``.
"""
from __future__ import annotations

import json
import logging
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("control-api")

INFRA_PROJECT_NAME = "ai-dev-factory-infra"
INFRA_SERVICE_NAME = "traefik"
INFRA_COMPOSE_REL = Path("deploy/infra/docker-compose.traefik.yml")
INFRA_SCRIPT_REL = Path("deploy/infra/start_traefik.sh")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 80

_NETWORK_MISSING_RE = ("network", "not found")

# Stale app-stack Traefik from pre-separation compose files.
_STALE_TRAEFIK_CONTAINER = "ai-dev-factory-traefik-1"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "deploy" / "infra").exists():
            return parent
    return here.parents[3]


def _expected_routes_dir() -> Path:
    """Lazy import avoids circular dependency with infra_service_manager."""
    from .infra_service_manager import resolve_proxy_routes_dir

    return resolve_proxy_routes_dir()


class TraefikManager:
    """Ensures the global Traefik service owns host port 80."""

    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        socket_factory=None,
        runner=None,
        sleeper=None,
    ) -> None:
        self.repo_root = repo_root or _repo_root()
        self.host = host
        self.port = port
        self.compose_file = self.repo_root / INFRA_COMPOSE_REL
        self.start_script = self.repo_root / INFRA_SCRIPT_REL
        self._socket_factory = socket_factory or socket.create_connection
        self._run = runner or subprocess.run
        self._sleep = sleeper or time.sleep

    # ── Docker metadata ───────────────────────────────────────────────

    def _run_cmd(self, cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
        try:
            result = self._run(
                cmd, capture_output=True, text=True, check=False, timeout=timeout
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return 1, "", f"{type(exc).__name__}: {exc}"
        return result.returncode, result.stdout or "", result.stderr or ""

    def infra_container_id(self) -> str | None:
        """Container id for the infra project's traefik service."""
        rc, out, _err = self._run_cmd([
            "docker", "compose",
            "-f", str(self.compose_file),
            "-p", INFRA_PROJECT_NAME,
            "ps", "--status", "running", "-q", INFRA_SERVICE_NAME,
        ])
        if rc != 0:
            return None
        cid = (out or "").strip().splitlines()
        return cid[0].strip() if cid else None

    def inspect_infra_container(self) -> dict[str, Any] | None:
        cid = self.infra_container_id()
        if not cid:
            return None
        rc, out, _err = self._run_cmd(["docker", "inspect", cid])
        if rc != 0 or not out.strip():
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None
        if not data:
            return None
        return data[0] if isinstance(data, list) else data

    @staticmethod
    def compose_labels_match(inspect_data: dict[str, Any]) -> bool:
        labels = inspect_data.get("Config", {}).get("Labels") or {}
        return (
            labels.get("com.docker.compose.project") == INFRA_PROJECT_NAME
            and labels.get("com.docker.compose.service") == INFRA_SERVICE_NAME
        )

    @staticmethod
    def publishes_host_port(
        inspect_data: dict[str, Any], port: int = DEFAULT_PORT
    ) -> bool:
        """True iff this container has a host binding on *port*."""
        bindings = (inspect_data.get("NetworkSettings") or {}).get("Ports") or {}
        entries = bindings.get(f"{port}/tcp")
        if not entries:
            return False
        for entry in entries:
            if not entry:
                continue
            if str(entry.get("HostPort")) == str(port):
                return True
        return False

    @staticmethod
    def routes_mount_matches(inspect_data: dict[str, Any]) -> bool:
        expected = _expected_routes_dir().resolve()
        for mount in inspect_data.get("Mounts") or []:
            if mount.get("Destination") != "/routes":
                continue
            source = Path(mount.get("Source", "")).expanduser().resolve()
            return source == expected
        return False

    def find_host_port_owner(self, port: int = DEFAULT_PORT) -> str | None:
        """Best-effort name of the container publishing *port* on the host."""
        rc, out, _err = self._run_cmd([
            "docker", "ps",
            "--format", "{{.Names}}\t{{.Ports}}",
        ])
        if rc != 0:
            return None
        needle = f":{port}->"
        for line in (out or "").splitlines():
            if needle not in line:
                continue
            name = line.split("\t", 1)[0].strip()
            if name:
                return name
        return None

    def _log_port_80_conflict(self, infra: dict[str, Any] | None) -> None:
        owner = self.find_host_port_owner()
        infra_name = None
        if infra:
            infra_name = (infra.get("Name") or "").lstrip("/")

        logger.warning("traefik: port %d is owned by another container/process", self.port)
        logger.warning("traefik: expected compose project = %s", INFRA_PROJECT_NAME)
        logger.warning("traefik: expected service = %s", INFRA_SERVICE_NAME)
        if infra_name:
            logger.warning(
                "traefik: infra container %s is running but does NOT publish host port %d",
                infra_name,
                self.port,
            )
        if owner:
            logger.warning("traefik: docker ps owner = %s", owner)
        logger.warning("traefik: stop stale container or run cleanup:")
        logger.warning("  docker stop %s", _STALE_TRAEFIK_CONTAINER)
        logger.warning("  docker rm %s", _STALE_TRAEFIK_CONTAINER)
        logger.warning("  bash deploy/infra/start_traefik.sh up")

    def _log_routes_mount_mismatch(self, infra: dict[str, Any]) -> None:
        expected = _expected_routes_dir()
        actual = None
        for mount in infra.get("Mounts") or []:
            if mount.get("Destination") == "/routes":
                actual = mount.get("Source")
                break
        logger.warning(
            "traefik: /routes mount mismatch — expected %s, container has %s",
            expected,
            actual,
        )

    # ── Probes ────────────────────────────────────────────────────────

    def is_listening(self, timeout: float = 0.5) -> bool:
        try:
            sock = self._socket_factory((self.host, self.port), timeout)
        except OSError:
            return False
        try:
            sock.close()
        except Exception:
            pass
        return True

    def is_running(self) -> bool:
        """Infra compose service reports a running container."""
        return self.infra_container_id() is not None

    def infra_owns_host_port(self) -> bool:
        """The infra Traefik container publishes host port 80."""
        infra = self.inspect_infra_container()
        if not infra:
            return False
        state = (infra.get("State") or {}).get("Status")
        if state != "running":
            return False
        if not self.compose_labels_match(infra):
            return False
        return self.publishes_host_port(infra, self.port)

    def _ready(self) -> bool:
        """Strong readiness: listening + infra container owns port 80 + routes mount."""
        if not self.is_listening():
            return False

        infra = self.inspect_infra_container()
        if not infra:
            return False
        if (infra.get("State") or {}).get("Status") != "running":
            return False
        if not self.compose_labels_match(infra):
            return False
        if not self.publishes_host_port(infra, self.port):
            return False
        if not self.routes_mount_matches(infra):
            self._log_routes_mount_mismatch(infra)
            return False
        return True

    # ── Lifecycle ─────────────────────────────────────────────────────

    def _compose_up(self) -> tuple[int, str, str]:
        return self._run_cmd(["bash", str(self.start_script), "up"], timeout=60)

    def _compose_down(self) -> tuple[int, str, str]:
        return self._run_cmd([
            "docker", "compose",
            "-f", str(self.compose_file),
            "-p", INFRA_PROJECT_NAME,
            "down", "--remove-orphans",
        ], timeout=60)

    @staticmethod
    def _looks_like_network_missing(stderr: str) -> bool:
        low = stderr.lower()
        return all(token in low for token in _NETWORK_MISSING_RE)

    @staticmethod
    def _looks_like_port_allocated(stderr: str) -> bool:
        low = stderr.lower()
        return "port is already allocated" in low or "address already in use" in low

    def _restart_infra_project(self) -> tuple[int, str, str]:
        """Single recovery: down + up on the infra project only."""
        self._compose_down()
        return self._compose_up()

    def wait_ready(self, timeout: float = 15.0, interval: float = 0.5) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._ready():
                return True
            self._sleep(interval)
        return self._ready()

    def ensure_running(self, timeout: float = 15.0) -> bool:
        if self._ready():
            logger.debug(
                "traefik: ready (infra %s owns host port %d)",
                INFRA_PROJECT_NAME,
                self.port,
            )
            return True

        infra = self.inspect_infra_container()
        listening = self.is_listening()
        infra_running = infra is not None and (infra.get("State") or {}).get("Status") == "running"
        infra_publishes = bool(infra and self.publishes_host_port(infra, self.port))

        if listening and infra_running and not infra_publishes:
            self._log_port_80_conflict(infra)
            logger.warning(
                "traefik: restarting infra project so traefik publishes host port %d",
                self.port,
            )
            rc, _out, err = self._restart_infra_project()
            if rc == 0:
                ok = self.wait_ready(timeout=timeout)
                if not ok:
                    self._log_port_80_conflict(self.inspect_infra_container())
                return ok
            if self._looks_like_port_allocated(err):
                self._log_port_80_conflict(infra)
            logger.error("traefik: infra restart failed rc=%d stderr=%s", rc, err.strip())
            return False

        if listening and not infra_publishes:
            self._log_port_80_conflict(infra)
            logger.info(
                "traefik: attempting infra start via %s (port %d is in use elsewhere)",
                self.start_script,
                self.port,
            )
            rc, _out, err = self._compose_up()
            if rc != 0:
                if self._looks_like_port_allocated(err):
                    logger.error(
                        "traefik: cannot start infra traefik — host port %d already "
                        "allocated. Stop the stale container listed above.",
                        self.port,
                    )
                else:
                    logger.error("traefik: start failed rc=%d stderr=%s", rc, err.strip())
                return False
            return self.wait_ready(timeout=timeout)

        if not listening:
            logger.info(
                "traefik: not listening on %s:%d — starting via %s",
                self.host, self.port, self.start_script,
            )

        rc, _out, err = self._compose_up()

        if rc != 0 and self._looks_like_network_missing(err):
            logger.warning(
                "traefik: docker reports a missing network, recreating the "
                "infra compose project (this never affects api/web). "
                "stderr: %s",
                err.strip(),
            )
            rc, _out, err = self._restart_infra_project()

        if rc != 0:
            if self._looks_like_port_allocated(err):
                self._log_port_80_conflict(infra)
            logger.error("traefik: start failed rc=%d stderr=%s", rc, err.strip())
            return False

        ok = self.wait_ready(timeout=timeout)
        if not ok:
            self._log_port_80_conflict(self.inspect_infra_container())
            logger.error(
                "traefik: started but infra traefik does not own host port %d "
                "within %.1fs",
                self.port,
                timeout,
            )
        return ok


def ensure_running(timeout: float = 15.0) -> bool:
    return TraefikManager().ensure_running(timeout=timeout)
