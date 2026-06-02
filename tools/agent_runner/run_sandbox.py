#!/usr/bin/env python3
"""Host-side sandbox-validation worker.

Runs the per-project deploy-validation pipeline on the **host** filesystem:

    .ai-dev-factory/scripts/bootstrap.sh
      → .ai-dev-factory/scripts/build.sh
        → .ai-dev-factory/scripts/start.sh
          → .ai-dev-factory/scripts/healthcheck.sh

…inside an isolated ``git worktree`` of the project. Each script is
**required** — if any of them is missing the run fails immediately
with a clear "required script missing: …" error. Silently skipping
missing scripts (the previous behaviour) used to report "sandbox:
success" with zero steps actually executed, masking real generation
failures upstream. The pipeline used to
live inside the API Docker container, which broke as soon as the
project_root pointed at a host-only path (``/Users/…``) that the container
cannot see. This script is invoked by the supervisor (``services/supervisor``),
which has already translated the container path to the host path via
``ContainerToHostMapper``.

Flow
----
1. Supervisor receives ``POST /sandbox/start`` with the container-side
   ``project_root``.
2. Supervisor maps it to the host path and spawns this worker with
   ``--project-root <host_path>``.
3. This worker writes its state to ``${RUNTIME_ROOT}/state/sandbox-{project_id}.json``
   so the supervisor's status endpoint can serve it back to the dashboard.

State + log layout (matches the analysis/scripts workers)
---------------------------------------------------------
    ${RUNTIME_ROOT}/state/sandbox-{project_id}.json   # latest snapshot
    ${RUNTIME_ROOT}/sandboxes/{sandbox_id}/state.json # per-run history
    ${RUNTIME_ROOT}/sandboxes/{sandbox_id}/run.log
    ${RUNTIME_ROOT}/sandboxes/{sandbox_id}/worktree/  # the isolated worktree

Worker stdout/stderr is captured by the supervisor and tee'd to
``${RUNTIME_ROOT}/logs/sandbox-{project_id}.log``. Step-by-step output
is also written to the per-run ``run.log`` for archival.

Robustness
----------
The previously container-side runner could hang forever during
``git worktree add``. This worker preserves every fix landed by PR #120:

* ``stdin=DEVNULL`` + ``start_new_session=True`` → safe ``killpg`` on timeout
* preflight: ``git`` on PATH? repo present? stale ``.git/index.lock``?
  leftover worktree path? — caught before any subprocess hang
* per-step subprocess timeout
* outer try/except guarantees ``state=failed`` on any unhandled error
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
import datetime
import fcntl
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

# Make sibling modules importable when this script is launched as
# ``python tools/agent_runner/run_sandbox.py …`` (the supervisor's
# canonical invocation form).
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from compose_utils import normalize_compose_project_name  # noqa: E402

# Cross-layer reach into the control_api services package — same
# pattern used by ``services/control_api/services/sandbox_manager.py``
# importing ``tools.agent_runner.compose_utils``. The proxy + Traefik
# helpers are small and stateless; importing them keeps the worker
# DRY relative to the dashboard's start path.
_PKG_ROOT = _THIS_DIR.parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from services.control_api.services.infra_service_manager import (  # noqa: E402
    ensure_required_infra,
    resolve_proxy_routes_dir,
)
from services.control_api.services.proxy_manager import (  # noqa: E402
    ProxyManager,
    build_sandbox_urls as _build_sandbox_urls,
)

logger = logging.getLogger("run_sandbox")

# Scripts are produced by the scripts-generation pipeline (`run_scripts.py`)
# and committed under `.ai-dev-factory/scripts/` at the project root, so
# they're naturally present in any git worktree carved from HEAD. We
# execute them with `cwd=<worktree>` so the scripts themselves can rely on
# the project root being the current directory (e.g. `npm install`,
# `docker compose up`).
#
# Every script here is **required**. Missing scripts fail the validation
# — silently skipping them used to surface as "sandbox: success" with no
# steps actually executed, which masked real generation failures.
_SCRIPTS_DIR = ".ai-dev-factory/scripts"
_REQUIRED_SCRIPTS = [
    "bootstrap.sh",
    "build.sh",
    "start.sh",
    "healthcheck.sh",
]
_SMOKE_SCRIPT = "smoke.sh"

_WORKTREE_TIMEOUT_SECONDS = int(
    os.environ.get("AI_DEV_FACTORY_SANDBOX_WORKTREE_TIMEOUT", "60")
)
_SCRIPT_TIMEOUT_SECONDS = int(
    os.environ.get("AI_DEV_FACTORY_SANDBOX_SCRIPT_TIMEOUT", "300")
)
_GIT_PRUNE_TIMEOUT_SECONDS = 30
_GIT_REMOVE_TIMEOUT_SECONDS = 30


# ── Path resolution ──────────────────────────────────────────────────────────


def _runtime_root() -> Path:
    """Resolve the canonical host runtime root.

    Order:
      1. ``AI_DEV_FACTORY_RUNTIME_ROOT`` env var (production / supervisor).
      2. Fallback to project_root/.ai-dev-factory (developer running the
         worker directly from a clone).
    """
    rr = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if rr:
        return Path(rr).expanduser().resolve()
    return Path.cwd() / ".ai-dev-factory"


def _sandbox_root() -> Path:
    """Resolve the top-level sandbox root from SANDBOX_ROOT, expanding ~."""
    raw = os.environ.get("SANDBOX_ROOT", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / "sandboxes"


def _project_name() -> str:
    """Return the project name from PROJECT_NAME or basename of AI_DEV_FACTORY_PROJECT_ROOT."""
    name = os.environ.get("PROJECT_NAME", "").strip()
    if name:
        return name
    project_root = os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", "").strip()
    if project_root:
        return Path(project_root).name
    return "default"


def _sandbox_base_dir() -> Path:
    p = _sandbox_root() / _project_name()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_dir() -> Path:
    p = _runtime_root() / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _latest_state_path(project_id: str) -> Path:
    return _state_dir() / f"sandbox-{project_id}.json"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _make_sandbox_id(project_id: str) -> str:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{project_id}-{ts}"


# ── Port registry ────────────────────────────────────────────────────────────

# Slot 0 is reserved for the main runtime (API 8080, web 3000).
# Each sandbox gets its own slot ≥ 1: api_port = 8080 + slot*100,
# web_port = 3000 + slot*100.

def _port_registry_paths() -> tuple[Path, Path]:
    base = _sandbox_base_dir()
    return base / "port-registry.json", base / ".port-registry.lock"


def _allocate_port_slot(sandbox_id: str) -> int:
    registry_path, lock_path = _port_registry_paths()
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            registry: dict[str, int] = {}
            if registry_path.exists():
                try:
                    registry = json.loads(registry_path.read_text())
                except (json.JSONDecodeError, OSError):
                    registry = {}
            used_slots = set(registry.values())
            slot = 1
            while slot in used_slots:
                slot += 1
            registry[sandbox_id] = slot
            registry_path.write_text(json.dumps(registry, indent=2))
            return slot
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _release_port_slot(sandbox_id: str) -> None:
    registry_path, lock_path = _port_registry_paths()
    if not registry_path.exists():
        return
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            try:
                registry: dict[str, int] = json.loads(registry_path.read_text())
            except (json.JSONDecodeError, OSError):
                return
            registry.pop(sandbox_id, None)
            registry_path.write_text(json.dumps(registry, indent=2))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


# ── Reverse proxy integration ────────────────────────────────────────────────


def _ensure_required_infra(log_path: Path) -> dict[str, bool]:
    """Ensure host-global infra (reverse proxy, …) before route
    registration and healthcheck. Never raises."""
    return ensure_required_infra(
        log=lambda line: _append_log(log_path, f"{line}\n"),
    )


def _register_proxy_route(
    sandbox_id: str,
    api_port: int,
    web_port: int,
    log_path: Path,
    *,
    web_host: str | None = None,
    api_host: str | None = None,
) -> str | None:
    """Write the sandbox route file under the host-global routes dir.

    Routes target the per-sandbox DNS aliases on ``ai-dev-factory-runtime``.

    Returns the registered API URL on success, None on failure.
    """
    routes_dir = resolve_proxy_routes_dir()
    try:
        urls = ProxyManager(
            routes_dir=routes_dir,
            auto_ensure_infra=False,
        ).register(
            sandbox_id,
            web_host=web_host,
            api_host=api_host,
            log=lambda line: _append_log(log_path, line),
        )
        _append_log(
            log_path,
            f"proxy: route registered sandbox={sandbox_id} dir={routes_dir} urls={urls}\n",
        )
        return urls.get("api")
    except Exception as exc:
        _append_log(log_path, f"proxy: route registration failed: {exc!r}\n")
        return None


def _wait_for_proxy_url(url: str, log_path: Path, *, timeout_s: int = 15) -> bool:
    """Poll the given URL until Traefik responds or the timeout expires.

    Any HTTP response (including 4xx/5xx) means the route is live.
    Returns False only when every attempt gets a connection-level error,
    indicating Traefik itself is unreachable (infra failure).
    Never raises.

    Retries here check route/Traefik reachability only (any HTTP response = Traefik is
    forwarding); backend readiness retries are handled in healthcheck.sh via
    HEALTHCHECK_RETRIES/HEALTHCHECK_DELAY.
    """
    for _ in range(timeout_s):
        try:
            urllib.request.urlopen(url, timeout=2)
            _append_log(log_path, "proxy: route active (backend healthy)\n")
            return True
        except urllib.error.HTTPError as e:
            # Any HTTP error response means Traefik forwarded the request.
            _append_log(log_path, f"proxy: route active (backend not healthy yet, http={e.code})\n")
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    _append_log(log_path, f"proxy: infra unreachable after {timeout_s}s\n")
    return False


def _log_proxy_backend_diagnostics(sandbox_id: str, log_path: Path) -> dict:
    """Probe backend aliases from inside Traefik; inspect api container; log results.

    Returns structured diagnostics for inclusion in validation.json.
    Never raises — all errors are logged and swallowed.
    """
    try:
        from services.control_api.services.traefik_manager import TraefikManager
        from services.control_api.services.proxy_route_files import (
            probe_backend_from_traefik_container,
        )
        from services.control_api.services.proxy_network import (
            sandbox_dns_aliases,
            sandbox_backend_urls,
        )
    except ImportError:
        return {}

    backend_urls = sandbox_backend_urls(sandbox_id)
    aliases = sandbox_dns_aliases(sandbox_id)

    try:
        traefik_cid = TraefikManager().infra_container_id()
    except Exception:
        traefik_cid = None

    probe_results = probe_backend_from_traefik_container(sandbox_id, container_id=traefik_cid)

    _append_log(
        log_path,
        f"proxy: backend diagnostics sandbox={sandbox_id}"
        f" traefik_container={traefik_cid}"
        f" aliases_api={aliases['api']}"
        f" aliases_web={aliases['web']}\n",
    )
    for svc, result in probe_results.items():
        _append_log(log_path, f"proxy: backend probe {svc}={result}\n")

    # Inspect Traefik container to retrieve its network membership.
    traefik_networks: list[str] = []
    if traefik_cid:
        try:
            ti = subprocess.run(
                ["docker", "inspect", traefik_cid],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if ti.returncode == 0 and ti.stdout.strip():
                td = json.loads(ti.stdout)
                if td:
                    traefik_networks = list(
                        td[0].get("NetworkSettings", {}).get("Networks", {}).keys()
                    )
                    _append_log(
                        log_path,
                        f"proxy: traefik container networks={traefik_networks}\n",
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass

    # Inspect the API container for runtime state and network membership.
    compose_project = normalize_compose_project_name(f"sandbox-{sandbox_id}")
    api_container_name = f"{compose_project}-api-1"
    api_container_info: dict = {
        "name": api_container_name,
        "status": "unknown",
        "restarts": 0,
        "health": "none",
        "networks": [],
    }
    try:
        inspect = subprocess.run(
            ["docker", "inspect", api_container_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if inspect.returncode == 0 and inspect.stdout.strip():
            try:
                data = json.loads(inspect.stdout)
                if data:
                    c = data[0]
                    state = c.get("State", {})
                    health = state.get("Health", {}) or {}
                    networks = list(c.get("NetworkSettings", {}).get("Networks", {}).keys())
                    api_container_info = {
                        "name": api_container_name,
                        "status": state.get("Status", "unknown"),
                        "restarts": c.get("RestartCount", 0),
                        "health": health.get("Status", "none"),
                        "networks": networks,
                    }
                    _append_log(
                        log_path,
                        f"proxy: api container ({api_container_name}):"
                        f" status={api_container_info['status']}"
                        f" restarts={api_container_info['restarts']}"
                        f" health={api_container_info['health']}"
                        f" networks={networks}\n",
                    )
            except (json.JSONDecodeError, KeyError):
                _append_log(log_path, f"proxy: api container ({api_container_name}): inspect parse failed\n")
        else:
            _append_log(log_path, f"proxy: api container ({api_container_name}): not found\n")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Classify the failure to distinguish DNS/network issues from crash loops.
    api_probe = probe_results.get("api", "")
    api_status = api_container_info["status"]
    api_restarts = api_container_info["restarts"]
    if api_restarts > 0 and api_status != "running":
        failure_type = "crash_loop"
    elif api_probe.startswith("failed:") and api_status == "running":
        failure_type = "dns_network"
    elif api_probe == "reachable" and api_status == "running":
        failure_type = "backend_app"
    else:
        failure_type = "unknown"

    return {
        "backend_urls": backend_urls,
        "aliases": aliases,
        "traefik_probe": probe_results,
        "traefik_networks": traefik_networks,
        "api_container": api_container_info,
        "failure_type": failure_type,
    }


def _unregister_proxy_route(
    sandbox_id: str,
    log_path: Path,
) -> None:
    """Remove the sandbox's route file from the host-global routes dir."""
    try:
        ProxyManager(
            routes_dir=resolve_proxy_routes_dir(),
            auto_ensure_infra=False,
        ).unregister(
            sandbox_id,
            remove_route_file=True,
            log=lambda line: _append_log(log_path, line),
        )
        _append_log(log_path, f"proxy: route unregistered for {sandbox_id}\n")
    except Exception as exc:
        _append_log(log_path, f"proxy: route unregister failed: {exc!r}\n")


def _write_sandbox_env(
    sandbox_dir: Path,
    sandbox_id: str,
    runtime_root: Path,
    project_root: Path,
    api_port: int,
    web_port: int,
    compose_project: str,
    supervisor_port: int,
) -> None:
    lines = [
        f"AI_DEV_FACTORY_RUNTIME_ROOT={runtime_root}",
        f"AI_DEV_FACTORY_PROJECT_ROOT={project_root}",
        f"AI_DEV_FACTORY_SUPERVISOR_PORT={supervisor_port}",
        f"AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}",
        f"API_PORT={api_port}",
        f"WEB_PORT={web_port}",
        f"COMPOSE_PROJECT_NAME={compose_project}",
        f"SANDBOX_ID={sandbox_id}",
        f"SANDBOX_ROOT={_sandbox_root()}",
        f"PROJECT_NAME={_project_name()}",
    ]
    (sandbox_dir / "deploy.env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state(state_path: Path, latest_state_path: Path, data: dict) -> None:
    """Persist state to both the per-run and the latest-state files atomically."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2)
    state_path.write_text(payload, encoding="utf-8")
    latest_state_path.parent.mkdir(parents=True, exist_ok=True)
    latest_state_path.write_text(payload, encoding="utf-8")


def _append_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text)
    # Mirror to stdout so the supervisor's log capture sees it too.
    sys.stdout.write(text)
    sys.stdout.flush()


# ── Git helpers (ported from sandbox_runner; PR #120 robustness) ─────────────


def _run_git(
    args: list[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
) -> tuple[int, str, str]:
    cmd = ["git", *args]
    _append_log(log_path, f"+ {' '.join(cmd)}  (cwd={cwd}, timeout={timeout}s)\n")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        _append_log(
            log_path,
            f"git command timed out after {timeout}s; process group killed\n",
        )
        if stdout:
            _append_log(log_path, stdout)
        if stderr:
            _append_log(log_path, stderr)
        raise

    if stdout:
        _append_log(log_path, stdout)
    if stderr:
        _append_log(log_path, stderr)
    _append_log(log_path, f"exit={proc.returncode}\n")
    return proc.returncode, stdout, stderr


def _preflight_worktree(
    project_root: Path, worktree_path: Path, log_path: Path
) -> str | None:
    if shutil.which("git") is None:
        return "git binary not found in PATH"

    if not project_root.exists():
        return f"project_root does not exist: {project_root}"

    git_dir = project_root / ".git"
    if not git_dir.exists():
        return f"project_root is not a git repository (no .git): {project_root}"

    lock_candidates = [
        git_dir / "index.lock" if git_dir.is_dir() else None,
        project_root / ".git/index.lock",
    ]
    for lock in (c for c in lock_candidates if c is not None):
        if lock.exists():
            try:
                lock.unlink()
                _append_log(log_path, f"removed stale lock: {lock}\n")
            except OSError as e:
                return f"could not remove stale index lock {lock}: {e}"

    if worktree_path.exists():
        _append_log(
            log_path,
            f"worktree path already exists: {worktree_path} — attempting cleanup\n",
        )
        try:
            rc, _out, err = _run_git(
                ["worktree", "remove", "--force", str(worktree_path)],
                cwd=project_root,
                log_path=log_path,
                timeout=_GIT_REMOVE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return "git worktree remove timed out cleaning up previous run"
        if rc != 0:
            try:
                shutil.rmtree(worktree_path)
                _append_log(log_path, f"removed stale dir: {worktree_path}\n")
            except OSError as e:
                return (
                    f"worktree path {worktree_path} could not be cleaned: "
                    f"git remove rc={rc} stderr={err.strip()[:200]} "
                    f"rmtree={e}"
                )

    try:
        _run_git(
            ["worktree", "prune"],
            cwd=project_root,
            log_path=log_path,
            timeout=_GIT_PRUNE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _append_log(log_path, "git worktree prune timed out (continuing)\n")

    return None


def _create_worktree(
    project_root: Path,
    worktree_path: Path,
    log_path: Path,
) -> tuple[bool, str | None]:
    _append_log(log_path, "\n--- creating git worktree ---\n")
    _append_log(log_path, f"worktree path: {worktree_path}\n")
    _append_log(log_path, f"timeout: {_WORKTREE_TIMEOUT_SECONDS}s\n")

    preflight_error = _preflight_worktree(project_root, worktree_path, log_path)
    if preflight_error is not None:
        _append_log(log_path, f"preflight failed: {preflight_error}\n")
        return False, preflight_error

    try:
        rc, _stdout, stderr = _run_git(
            ["worktree", "add", str(worktree_path), "HEAD"],
            cwd=project_root,
            log_path=log_path,
            timeout=_WORKTREE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, (
            f"git worktree add timed out after {_WORKTREE_TIMEOUT_SECONDS}s"
        )
    except OSError as e:
        return False, f"git worktree add could not run: {e}"

    if rc != 0:
        return False, (
            f"git worktree add exited {rc}: {stderr.strip()[:500] or '<no stderr>'}"
        )

    _append_log(log_path, "worktree created\n")
    return True, None


# ── Script pipeline ──────────────────────────────────────────────────────────


def _run_scripts(
    worktree_path: Path,
    state_path: Path,
    latest_state_path: Path,
    log_path: Path,
    state_base: dict,
    extra_env: dict | None = None,
    on_step_start: Callable[[str], None] | None = None,
    on_step_complete: Callable[[str], bool | None] | None = None,
) -> tuple[bool, str | None, list[dict]]:
    steps: list[dict] = []
    scripts_dir_abs = worktree_path / _SCRIPTS_DIR

    _append_log(
        log_path,
        f"\n--- resolving operational scripts ---\n"
        f"scripts dir (relative): {_SCRIPTS_DIR}\n"
        f"scripts dir (absolute): {scripts_dir_abs}\n",
    )

    for script_name in _REQUIRED_SCRIPTS:
        script_rel = f"{_SCRIPTS_DIR}/{script_name}"
        script_path = worktree_path / script_rel
        _append_log(log_path, f"resolved script path: {script_path}\n")

        if not script_path.exists():
            error = f"required script missing: {script_rel}"
            _append_log(log_path, f"{error}\n")
            step = {
                "name": script_name, "status": "failed",
                "exit_code": None,
                "started_at": _now_iso(), "finished_at": _now_iso(),
            }
            steps.append(step)
            _write_state(state_path, latest_state_path, {
                **state_base, "last_step": script_name, "steps": steps,
            })
            return False, error, steps

        step_started = _now_iso()
        if on_step_start is not None:
            on_step_start(script_name)
        _append_log(
            log_path,
            f"\n--- {script_name} ({script_rel}) ---\n",
        )
        _write_state(state_path, latest_state_path, {
            **state_base, "last_step": script_name, "steps": steps,
        })

        # Run from the worktree root so scripts can use project-relative
        # paths (e.g. `npm install`, `docker compose up`).
        script_env = {**os.environ, **(extra_env or {})}
        try:
            result = subprocess.run(
                ["bash", script_rel],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                timeout=_SCRIPT_TIMEOUT_SECONDS,
                env=script_env,
            )
        except subprocess.TimeoutExpired:
            step = {
                "name": script_name, "status": "failed", "exit_code": -1,
                "started_at": step_started, "finished_at": _now_iso(),
            }
            steps.append(step)
            _append_log(log_path, f"{script_name} timed out\n")
            return False, f"{script_name} timed out", steps

        if result.stdout:
            _append_log(log_path, result.stdout)
        if result.stderr:
            _append_log(log_path, result.stderr)

        step = {
            "name": script_name,
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "started_at": step_started,
            "finished_at": _now_iso(),
        }
        steps.append(step)
        _write_state(state_path, latest_state_path, {
            **state_base, "last_step": script_name, "steps": steps,
        })

        if result.returncode != 0:
            return False, f"{script_name} failed (exit {result.returncode})", steps

        if on_step_complete is not None:
            cont = on_step_complete(script_name)
            if cont is False:
                return False, "post-start hook failed", steps

    return True, None, steps


# ── Stop script ─────────────────────────────────────────────────────────────


def _run_stop_script(
    worktree_path: Path,
    log_path: Path,
    extra_env: dict | None = None,
) -> None:
    """Execute stop.sh from the worktree as a cleanup step.

    Non-blocking to cleanup: a non-zero exit or missing script is logged
    but does not prevent the rest of the teardown from proceeding.
    """
    stop_rel = f"{_SCRIPTS_DIR}/stop.sh"
    stop_path = worktree_path / stop_rel
    if not stop_path.exists():
        _append_log(log_path, f"stop.sh not found at {stop_path}, skipping\n")
        return

    _append_log(log_path, f"\n--- stop.sh ({stop_rel}) ---\n")
    script_env = {**os.environ, **(extra_env or {})}
    try:
        result = subprocess.run(
            ["bash", stop_rel],
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            timeout=_SCRIPT_TIMEOUT_SECONDS,
            env=script_env,
        )
        if result.stdout:
            _append_log(log_path, result.stdout)
        if result.stderr:
            _append_log(log_path, result.stderr)
        if result.returncode != 0:
            _append_log(
                log_path,
                f"stop.sh exited {result.returncode} (continuing cleanup)\n",
            )
        else:
            _append_log(log_path, "stop.sh completed\n")
    except subprocess.TimeoutExpired:
        _append_log(
            log_path,
            f"stop.sh timed out after {_SCRIPT_TIMEOUT_SECONDS}s (continuing cleanup)\n",
        )
    except OSError as exc:
        _append_log(log_path, f"stop.sh failed to run: {exc} (continuing cleanup)\n")


# ── Smoke tests + validation artifact + fix proposal ────────────────────────


def _run_smoke_tests(
    worktree_path: Path,
    log_path: Path,
    extra_env: dict | None = None,
) -> tuple[str, str | None]:
    """Run smoke.sh if present; return (smoke_status, failing_step).

    smoke_status: "skipped" | "success" | "failed"
    failing_step: "smoke" when failed, None otherwise.
    """
    smoke_rel = f"{_SCRIPTS_DIR}/{_SMOKE_SCRIPT}"
    smoke_path = worktree_path / smoke_rel

    if not smoke_path.exists():
        _append_log(log_path, f"\n--- smoke tests: {smoke_rel} not found, skipping ---\n")
        return "skipped", None

    _append_log(log_path, f"\n--- smoke tests: {smoke_rel} ---\n")
    script_env = {**os.environ, **(extra_env or {})}

    try:
        result = subprocess.run(
            ["bash", smoke_rel],
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            timeout=_SCRIPT_TIMEOUT_SECONDS,
            env=script_env,
        )
    except subprocess.TimeoutExpired:
        _append_log(log_path, f"smoke tests timed out after {_SCRIPT_TIMEOUT_SECONDS}s\n")
        return "failed", "smoke"

    if result.stdout:
        _append_log(log_path, result.stdout)
    if result.stderr:
        _append_log(log_path, result.stderr)

    if result.returncode == 0:
        _append_log(log_path, "smoke tests passed\n")
        return "success", None

    _append_log(log_path, f"smoke tests failed (exit {result.returncode})\n")
    return "failed", "smoke"


def _write_validation_json(
    sandbox_runtime_root: Path,
    sandbox_id: str,
    healthcheck_status: str,
    smoke_status: str,
    failing_step: str | None,
    proxy_urls: dict[str, str],
    ports: dict[str, int],
    started_at: str,
    log_path: Path,
    *,
    backend_diagnostics: dict | None = None,
) -> Path:
    """Write validation.json to sandbox_runtime_root; return the path."""
    data = {
        "sandbox_id": sandbox_id,
        "healthcheck_status": healthcheck_status,
        "smoke_status": smoke_status,
        "failing_step": failing_step,
        "proxy_urls": proxy_urls,
        "ports": ports,
        "timestamps": {
            "started_at": started_at,
            "finished_at": _now_iso(),
        },
        "log_path": str(log_path),
    }
    if backend_diagnostics is not None:
        data["backend_diagnostics"] = backend_diagnostics
    out = sandbox_runtime_root / "validation.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _append_log(log_path, f"validation.json written to {out}\n")
    return out


def _call_fix_proposer(
    sandbox_runtime_root: Path,
    validation_json_path: Path,
    worktree_path: Path,
    log_path: Path,
) -> None:
    """Pipe validation context to AI_DEV_FACTORY_EXEC_CMD; write fix-proposal.md.

    Only called when AI_DEV_FACTORY_EXEC_CMD is set and smoke tests failed.
    Never modifies files outside sandbox_runtime_root.
    """
    exec_cmd = os.environ.get("AI_DEV_FACTORY_EXEC_CMD", "").strip()
    if not exec_cmd:
        return

    _append_log(log_path, "\n--- calling AI fix proposer ---\n")

    context_parts: list[str] = []

    if validation_json_path.exists():
        context_parts.append(
            f"=== validation.json ===\n{validation_json_path.read_text(encoding='utf-8')}"
        )

    deploy_yml = worktree_path / ".ai-dev-factory" / "deploy.yml"
    if deploy_yml.exists():
        context_parts.append(
            f"=== deploy.yml ===\n{deploy_yml.read_text(encoding='utf-8')}"
        )

    scripts_dir = worktree_path / _SCRIPTS_DIR
    if scripts_dir.exists():
        artifact_list = "\n".join(
            str(f.relative_to(worktree_path))
            for f in sorted(scripts_dir.iterdir())
            if f.is_file()
        )
        context_parts.append(f"=== allowed deployment artifacts ===\n{artifact_list}")

    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        context_parts.append(
            "=== recent run.log (last 200 lines) ===\n" + "\n".join(lines[-200:])
        )

    context = "\n\n".join(context_parts)

    try:
        result = subprocess.run(
            exec_cmd,
            shell=True,
            input=context,
            capture_output=True,
            text=True,
            cwd=str(worktree_path),
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        _append_log(log_path, "fix proposer timed out\n")
        return
    except OSError as exc:
        _append_log(log_path, f"fix proposer failed to run: {exc}\n")
        return

    if result.stderr:
        _append_log(log_path, f"fix proposer stderr: {result.stderr[:500]}\n")

    proposal_path = sandbox_runtime_root / "fix-proposal.md"
    proposal_path.write_text(result.stdout, encoding="utf-8")
    _append_log(log_path, f"fix-proposal.md written to {proposal_path}\n")


# ── Main pipeline ────────────────────────────────────────────────────────────


def _start_sandbox_supervisor(
    supervisor_port: int,
    sandbox_runtime_root: Path,
    log_path: Path,
) -> subprocess.Popen | None:
    """Spawn a per-sandbox supervisor bound to *supervisor_port* with its own runtime root.

    Writes ``{sandbox_runtime_root}/supervisor.pid`` so SandboxManager.destroy()
    can SIGTERM the process on cleanup. Returns the Popen handle, or None on error.
    """
    repo_root = Path(__file__).resolve().parents[2]
    supervisor_env = {
        **os.environ,
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(sandbox_runtime_root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    cmd = [
        sys.executable, "-m", "uvicorn",
        "services.supervisor.main:app",
        "--host", "127.0.0.1",
        "--port", str(supervisor_port),
    ]
    _append_log(
        log_path,
        f"\n--- starting sandbox supervisor on port {supervisor_port} ---\n"
        f"runtime_root: {sandbox_runtime_root}\n"
        f"command: {' '.join(cmd)}\n",
    )
    try:
        sup_log = sandbox_runtime_root / "supervisor.log"
        with sup_log.open("a", encoding="utf-8") as sup_fh:
            proc = subprocess.Popen(
                cmd,
                cwd=str(repo_root),
                env=supervisor_env,
                stdin=subprocess.DEVNULL,
                stdout=sup_fh,
                stderr=sup_fh,
                start_new_session=True,
            )
        pid_path = sandbox_runtime_root / "supervisor.pid"
        pid_path.write_text(
            json.dumps({"pid": proc.pid, "port": supervisor_port}),
            encoding="utf-8",
        )
        _append_log(log_path, f"sandbox supervisor started pid={proc.pid}\n")
        return proc
    except OSError as exc:
        _append_log(log_path, f"sandbox supervisor failed to start: {exc}\n")
        return None


def _stop_sandbox_supervisor(
    proc: subprocess.Popen | None,
    sandbox_runtime_root: Path,
    log_path: Path,
) -> None:
    """Terminate the sandbox supervisor subprocess."""
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except (subprocess.TimeoutExpired, OSError):
            pass
    except OSError:
        pass
    pid_path = sandbox_runtime_root / "supervisor.pid"
    try:
        pid_path.unlink()
    except OSError:
        pass
    _append_log(log_path, "sandbox supervisor stopped\n")


def _do_sandbox(project_id: str, project_root: Path, sandbox_id: str, mode: str = "validation") -> int:
    base_dir = _sandbox_base_dir()
    sandbox_dir = base_dir / sandbox_id
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    state_path = sandbox_dir / "state.json"
    log_path = sandbox_dir / "run.log"
    worktree_path = sandbox_dir / "worktree"
    latest_state_path = _latest_state_path(project_id)

    # Allocate an isolated port slot before creating the worktree so ports
    # are visible in state from the very first write.
    slot = _allocate_port_slot(sandbox_id)
    api_port = 8080 + slot * 100
    web_port = 3000 + slot * 100
    supervisor_port = 8090 + slot

    # Sandbox IDs use a UTC timestamp like ``20260522T204456`` whose
    # uppercase ``T`` is rejected by Docker Compose. Normalise the
    # project name so it always matches ``^[a-z0-9][a-z0-9_-]*$`` while
    # remaining unique per sandbox run.
    compose_project = normalize_compose_project_name(f"sandbox-{sandbox_id}")
    ports = {"api_port": api_port, "web_port": web_port}

    # Each sandbox gets its own isolated runtime root so its supervisor serves
    # only that sandbox's state, not the main runtime state.
    sandbox_runtime_root = sandbox_dir / "runtime"
    sandbox_runtime_root.mkdir(parents=True, exist_ok=True)
    for subdir in ("state", "logs", "runs"):
        (sandbox_runtime_root / subdir).mkdir(exist_ok=True)

    _write_sandbox_env(
        sandbox_dir, sandbox_id, sandbox_runtime_root, project_root,
        api_port, web_port, compose_project, supervisor_port,
    )

    started_at = _now_iso()
    state_base = {
        "state": "validating",
        "mode": mode,
        "sandbox_id": sandbox_id,
        "project_id": project_id,
        "started_at": started_at,
        "finished_at": None,
        "error": None,
        "last_step": "worktree",
        "steps": [],
        "ports": ports,
        "worktree_path": str(worktree_path),
        "compose_project": compose_project,
        "project_root": str(project_root),
    }
    _write_state(state_path, latest_state_path, state_base)
    _append_log(log_path, f"=== sandbox {sandbox_id} started {started_at} ===\n")
    _append_log(log_path, f"project_root: {project_root}\n")
    _append_log(log_path, f"runtime_root: {_runtime_root()}\n")
    _append_log(log_path, f"sandbox_runtime_root: {sandbox_runtime_root}\n")
    _append_log(log_path, f"sandbox_dir: {sandbox_dir}\n")
    _append_log(
        log_path,
        f"port_slot: {slot}  api_port: {api_port}  web_port: {web_port}"
        f"  supervisor_port: {supervisor_port}\n",
    )
    raw_compose = f"sandbox-{sandbox_id}"
    if compose_project != raw_compose:
        _append_log(
            log_path,
            f"compose_project: {compose_project}  (normalised from {raw_compose!r})\n",
        )
    else:
        _append_log(log_path, f"compose_project: {compose_project}\n")

    # Sandbox-aware env injected into every operational script
    # subprocess. Key invariants:
    #
    #   * SANDBOX_*_URL: pretty reverse-proxy URLs. healthcheck.sh
    #     prefers these over ``localhost:<port>`` so a sandbox-mode
    #     healthcheck validates the SAME endpoint humans will use in
    #     the browser, not a backdoor on a host port.
    #
    #   * SUPERVISOR_URL: how containers reach the host supervisor
    #     (``host.docker.internal``, NOT resolvable from host scripts).
    #     Kept for compose env interpolation.
    #
    #   * SUPERVISOR_HEALTH_URL: how host-side scripts probe the
    #     supervisor (loopback, ``127.0.0.1``). Without this split,
    #     healthcheck.sh would curl ``host.docker.internal`` from
    #     the host shell and fail every time.
    sandbox_urls = _build_sandbox_urls(sandbox_id)
    extra_env = {
        "API_PORT": str(api_port),
        "WEB_PORT": str(web_port),
        "COMPOSE_PROJECT_NAME": compose_project,
        "SANDBOX_ID": sandbox_id,
        "SANDBOX_WEB_URL": sandbox_urls["web"],
        "SANDBOX_API_URL": sandbox_urls["api"],
        "AI_DEV_FACTORY_SUPERVISOR_PORT": str(supervisor_port),
        "AI_DEV_FACTORY_SUPERVISOR_URL": f"http://host.docker.internal:{supervisor_port}",
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": f"http://127.0.0.1:{supervisor_port}",
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(sandbox_runtime_root),
        "SANDBOX_ROOT": str(_sandbox_root()),
        "PROJECT_NAME": _project_name(),
    }

    # Per-sandbox supervisor — started ONCE here. start.sh must not
    # spawn a second supervisor on the same port (see
    # AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED below).
    supervisor_proc = _start_sandbox_supervisor(
        supervisor_port, sandbox_runtime_root, log_path
    )
    if supervisor_proc is not None:
        extra_env["AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED"] = "1"

    # Infra first; routes are registered after start.sh once compose is up
    # and Traefik is attached to the environment network.
    _ensure_required_infra(log_path)

    _proxy_diagnostics: list[dict] = [{}]

    def _after_start(script_name: str) -> bool | None:
        if script_name != "start.sh":
            return None
        api_url = _register_proxy_route(
            sandbox_id,
            api_port,
            web_port,
            log_path,
        )
        if not api_url:
            return False
        ok = _wait_for_proxy_url(api_url, log_path)
        _proxy_diagnostics[0] = _log_proxy_backend_diagnostics(sandbox_id, log_path)
        return ok

    # Set to True in environment mode on success to skip teardown in finally.
    keep_environment = False

    try:
        ok, error = _create_worktree(project_root, worktree_path, log_path)
        if not ok:
            _append_log(log_path, f"worktree creation failed: {error}\n")
            _write_state(state_path, latest_state_path, {
                **state_base,
                "state": "failed",
                "finished_at": _now_iso(),
                "error": error,
            })
            return 1

        success, error, steps = _run_scripts(
            worktree_path, state_path, latest_state_path, log_path, state_base,
            extra_env=extra_env,
            on_step_complete=_after_start,
        )

        # Derive healthcheck_status from the steps list.
        healthcheck_status = "skipped"
        for step in steps:
            if step["name"] == "healthcheck.sh":
                healthcheck_status = step["status"]

        # Run smoke tests only after all required scripts (incl. healthcheck) pass.
        smoke_status = "skipped"
        failing_step: str | None = None
        if success and mode == "validation":
            smoke_status, smoke_fail = _run_smoke_tests(worktree_path, log_path, extra_env)
            if smoke_fail is not None:
                failing_step = smoke_fail
                success = False
                error = "smoke tests failed"
        elif not success and steps:
            failing_step = steps[-1]["name"]

        # Always write validation.json so the result is observable.
        validation_json_path = _write_validation_json(
            sandbox_runtime_root, sandbox_id,
            healthcheck_status, smoke_status, failing_step,
            {"web": sandbox_urls["web"], "api": sandbox_urls["api"]},
            ports, started_at, log_path,
            backend_diagnostics=_proxy_diagnostics[0] or None,
        )

        # If smoke tests failed and an AI exec_cmd is configured, generate a fix proposal.
        if smoke_status == "failed":
            _call_fix_proposer(
                sandbox_runtime_root, validation_json_path, worktree_path, log_path
            )

        finished_at = _now_iso()
        if success and mode == "environment":
            # Leave compose services and supervisor running; worker exits cleanly.
            keep_environment = True
            _write_state(state_path, latest_state_path, {
                **state_base,
                "state": "environment",
                "finished_at": finished_at,
                "error": None,
                "last_step": steps[-1]["name"] if steps else state_base["last_step"],
                "steps": steps,
                "healthcheck_status": healthcheck_status,
                "smoke_status": smoke_status,
            })
            _append_log(
                log_path,
                f"\n=== sandbox {sandbox_id} environment ready {finished_at} ===\n",
            )
            return 0
        else:
            final_state = "validated" if success else "failed"
            last_step = (
                failing_step
                if failing_step
                else (steps[-1]["name"] if steps else state_base["last_step"])
            )
            _write_state(state_path, latest_state_path, {
                **state_base,
                "state": final_state,
                "finished_at": finished_at,
                "error": error,
                "last_step": last_step,
                "steps": steps,
                "healthcheck_status": healthcheck_status,
                "smoke_status": smoke_status,
            })
            outcome = "validated" if success else "failed"
            _append_log(
                log_path, f"\n=== sandbox {sandbox_id} {outcome} {finished_at} ===\n"
            )
            return 0 if success else 1

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        logger.exception(
            "sandbox: unhandled error project=%s sandbox=%s", project_id, sandbox_id
        )
        _append_log(log_path, f"\nunhandled exception: {e}\n{tb}\n")
        _write_state(state_path, latest_state_path, {
            **state_base,
            "state": "failed",
            "finished_at": _now_iso(),
            "error": f"unhandled exception in sandbox runner: {e}",
        })
        return 1
    finally:
        if not keep_environment:
            if worktree_path.exists():
                _run_stop_script(worktree_path, log_path, extra_env)
            _stop_sandbox_supervisor(supervisor_proc, sandbox_runtime_root, log_path)
            # Drop the proxy route so an orphan subdomain isn't left
            # pointing at a recycled port. ``keep_environment=True``
            # (sandbox-as-environment runs) intentionally leaves the
            # route in place so the operator can keep browsing it.
            _unregister_proxy_route(sandbox_id, log_path)
            _release_port_slot(sandbox_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Host-side sandbox validation worker"
    )
    parser.add_argument("--project-root", required=True,
                        help="Host filesystem path to the project (already mapped)")
    parser.add_argument("--project-id", required=True,
                        help="Project identifier used to locate state/log files")
    parser.add_argument(
        "--mode",
        choices=["validation", "environment"],
        default="validation",
        help="validation: deploy+test then teardown; environment: deploy and stay running",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    project_root = Path(args.project_root).expanduser().resolve()
    project_id = args.project_id
    sandbox_id = _make_sandbox_id(project_id)

    logger.info(
        "sandbox worker start project_id=%s project_root=%s sandbox_id=%s mode=%s runtime_root=%s",
        project_id, project_root, sandbox_id, args.mode, _runtime_root(),
    )

    rc = _do_sandbox(project_id, project_root, sandbox_id, mode=args.mode)
    sys.exit(rc)


if __name__ == "__main__":
    main()
