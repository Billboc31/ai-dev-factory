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
import datetime
import fcntl
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import traceback
from pathlib import Path

# Make sibling modules importable when this script is launched as
# ``python tools/agent_runner/run_sandbox.py …`` (the supervisor's
# canonical invocation form).
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from compose_utils import normalize_compose_project_name  # noqa: E402

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

    # Every key here is exported into the subprocess env of every
    # operational script (bootstrap/build/start/healthcheck/...). The
    # scripts read API_PORT / WEB_PORT / AI_DEV_FACTORY_SUPERVISOR_*
    # to expose the isolated sandbox endpoints instead of the main
    # runtime's hardcoded 8080/3000/8090 — otherwise healthchecks would
    # silently probe the main runtime and report green even when the
    # sandbox itself never came up.
    #
    # AI_DEV_FACTORY_RUNTIME_ROOT is included so scripts that resolve
    # state/logs paths land inside the per-sandbox runtime tree rather
    # than the shared host runtime root.
    extra_env = {
        "API_PORT": str(api_port),
        "WEB_PORT": str(web_port),
        "COMPOSE_PROJECT_NAME": compose_project,
        "SANDBOX_ID": sandbox_id,
        "AI_DEV_FACTORY_SUPERVISOR_PORT": str(supervisor_port),
        "AI_DEV_FACTORY_SUPERVISOR_URL": f"http://host.docker.internal:{supervisor_port}",
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(sandbox_runtime_root),
        "SANDBOX_ROOT": str(_sandbox_root()),
        "PROJECT_NAME": _project_name(),
    }

    supervisor_proc = _start_sandbox_supervisor(supervisor_port, sandbox_runtime_root, log_path)

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
            })
            _append_log(
                log_path,
                f"\n=== sandbox {sandbox_id} environment ready {finished_at} ===\n",
            )
            return 0
        else:
            final_state = "validated" if success else "failed"
            _write_state(state_path, latest_state_path, {
                **state_base,
                "state": final_state,
                "finished_at": finished_at,
                "error": error,
                "last_step": steps[-1]["name"] if steps else state_base["last_step"],
                "steps": steps,
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
