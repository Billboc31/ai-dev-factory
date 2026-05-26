"""Idempotent auto-start manager for the global Traefik reverse proxy.

The reverse proxy lives in ``deploy/infra/docker-compose.traefik.yml``
under the dedicated compose project ``ai-dev-factory-infra``. It is
**single-instance per host** — sandbox compose runs must never spawn
their own Traefik (that would conflict on port 80).

Operational flow this module supports::

    1. SandboxManager.start() / ProxyManager.register() — both
       implicitly call ``ensure_running()`` so the user never has to
       remember to start Traefik manually.

    2. ``ensure_running()`` is idempotent: returns True quickly when
       Traefik is already listening on port 80.

    3. If Traefik isn't listening, it shells out to the canonical
       ``deploy/infra/start_traefik.sh up`` script (which itself uses
       ``docker compose -f deploy/infra/docker-compose.traefik.yml -p
       ai-dev-factory-infra up -d traefik``).

    4. A common docker failure on local boxes is::

           Error response from daemon: network … not found

       triggered by a stale named-network from a previous run. The
       manager detects that on stderr, runs ``compose down
       --remove-orphans`` to clean up, then retries ``up``. Only the
       infra project is touched — the application stack (``api`` /
       ``web``) is never affected.

The module is also safe to import from worker contexts that don't
have docker available: ``ensure_running`` returns False and logs a
warning rather than crashing.
"""
from __future__ import annotations

import logging
import socket
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("control-api")

# Single source of truth — both ``start_traefik.sh`` and this module
# must agree on the compose project name, otherwise ``docker compose
# ps`` lookups would target the wrong project and ``ensure_running``
# would loop forever.
INFRA_PROJECT_NAME = "ai-dev-factory-infra"
INFRA_COMPOSE_REL = Path("deploy/infra/docker-compose.traefik.yml")
INFRA_SCRIPT_REL = Path("deploy/infra/start_traefik.sh")

# Traefik publishes the ``web`` entryPoint on host port 80. The probe
# uses a raw TCP connect rather than HTTP so we don't depend on
# Traefik's response shape (which changes across v2/v3) — any
# successful TCP handshake means "listening".
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 80

# Match docker errors that indicate the named-network referenced by the
# infra compose project no longer exists. The exact wording is::
#
#     Error response from daemon: network <id> not found
#
# This shows up when the user has run ``docker network prune`` or the
# Docker daemon was restarted. The recovery path is safe: only the
# infra project is taken down + restarted.
_NETWORK_MISSING_RE = ("network", "not found")


def _repo_root() -> Path:
    """Locate the repository root (the parent of ``services/`` and
    ``deploy/``). Walks up from this file rather than relying on cwd."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "deploy" / "infra").exists():
            return parent
    # Fallback: 4 levels up matches the layout
    # ``services/control_api/services/traefik_manager.py``.
    return here.parents[3]


class TraefikManager:
    """Ensures the global Traefik service is up and listening on port 80.

    Inject *socket_factory* and *runner* in tests to avoid touching the
    host docker daemon or the network stack.
    """

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
        # Indirection points for tests. By default we use the real
        # ``socket``/``subprocess.run``/``time.sleep`` so this class is
        # production-ready without mocks.
        self._socket_factory = socket_factory or socket.create_connection
        self._run = runner or subprocess.run
        self._sleep = sleeper or time.sleep

    # ── Probes ────────────────────────────────────────────────────────

    def is_listening(self, timeout: float = 0.5) -> bool:
        """TCP connect on ``host:port``. Cheap and protocol-agnostic."""
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
        """``docker compose ps`` against the infra project. Returns True
        iff the ``traefik`` container is in the *running* state.

        This is stronger than ``is_listening`` because a different
        process bound to port 80 (a stray nginx, a previous run's
        leftover container under a different name, …) would pass the
        TCP probe but is NOT what we want — ``ensure_running`` would
        skip restarting Traefik and proxy registrations would never
        reach a working reverse proxy.
        """
        cmd = [
            "docker", "compose",
            "-f", str(self.compose_file),
            "-p", INFRA_PROJECT_NAME,
            "ps", "--status", "running", "-q", "traefik",
        ]
        try:
            result = self._run(
                cmd, capture_output=True, text=True, check=False, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        if result.returncode != 0:
            return False
        return bool((result.stdout or "").strip())

    # ── Lifecycle ─────────────────────────────────────────────────────

    def _compose_up(self) -> tuple[int, str, str]:
        """Run the canonical startup script. Returns (rc, stdout, stderr)."""
        cmd = ["bash", str(self.start_script), "up"]
        try:
            result = self._run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return 1, "", f"{type(exc).__name__}: {exc}"
        return result.returncode, result.stdout or "", result.stderr or ""

    def _compose_down(self) -> tuple[int, str, str]:
        """Tear down the infra project (only). Used for stale-state recovery."""
        cmd = [
            "docker", "compose",
            "-f", str(self.compose_file),
            "-p", INFRA_PROJECT_NAME,
            "down", "--remove-orphans",
        ]
        try:
            result = self._run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return 1, "", f"{type(exc).__name__}: {exc}"
        return result.returncode, result.stdout or "", result.stderr or ""

    @staticmethod
    def _looks_like_network_missing(stderr: str) -> bool:
        low = stderr.lower()
        return all(token in low for token in _NETWORK_MISSING_RE)

    def wait_ready(self, timeout: float = 15.0, interval: float = 0.5) -> bool:
        """Poll ``is_listening`` until True or the deadline elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_listening():
                return True
            self._sleep(interval)
        return self.is_listening()

    def ensure_running(self, timeout: float = 15.0) -> bool:
        """Best-effort idempotent startup. Returns True iff Traefik is
        listening on port 80 by the end of the call.

        Never raises — proxy registration must remain best-effort so a
        misconfigured docker doesn't crash sandbox creation. Callers
        that need a hard guarantee can check the return value.
        """
        if self.is_listening():
            logger.debug("traefik: already listening on %s:%d", self.host, self.port)
            return True

        logger.info(
            "traefik: not listening on %s:%d — starting via %s",
            self.host, self.port, self.start_script,
        )
        rc, _out, err = self._compose_up()

        # Recovery path: stale named-network leftover from a previous run.
        if rc != 0 and self._looks_like_network_missing(err):
            logger.warning(
                "traefik: docker reports a missing network, recreating the "
                "infra compose project (this never affects api/web). "
                "stderr: %s",
                err.strip(),
            )
            self._compose_down()
            rc, _out, err = self._compose_up()

        if rc != 0:
            logger.error(
                "traefik: start failed rc=%d stderr=%s", rc, err.strip()
            )
            return False

        ok = self.wait_ready(timeout=timeout)
        if not ok:
            logger.error(
                "traefik: started but did not become ready within %.1fs "
                "on %s:%d",
                timeout, self.host, self.port,
            )
        return ok


# Module-level convenience function — callers that don't need the
# class form (most of them) can just::
#
#     from services.control_api.services.traefik_manager import ensure_running
#     ensure_running()
#
# This is the seam ``ProxyManager.register`` uses by default.
def ensure_running(timeout: float = 15.0) -> bool:
    return TraefikManager().ensure_running(timeout=timeout)
