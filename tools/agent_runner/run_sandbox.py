#!/usr/bin/env python3
"""Host-side sandbox-validation worker.

Runs the per-project deploy-validation pipeline on the **host** filesystem:

    bootstrap.sh → build.sh → start.sh → healthcheck.sh

…inside an isolated ``git worktree`` of the project. The pipeline used to
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
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import traceback
from pathlib import Path

logger = logging.getLogger("run_sandbox")

# Scripts run inside the worktree, in this order. A missing script is
# treated as "skipped" — that's how the pipeline supports projects that
# don't have every artefact yet.
_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]

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


def _sandbox_base_dir() -> Path:
    p = _runtime_root() / "sandboxes"
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
) -> tuple[bool, str | None, list[dict]]:
    steps: list[dict] = []

    for script_name in _SCRIPTS:
        script_path = worktree_path / script_name

        if not script_path.exists():
            _append_log(log_path, f"\n--- {script_name}: not found, skipping ---\n")
            steps.append({
                "name": script_name, "status": "skipped",
                "exit_code": None, "started_at": None, "finished_at": None,
            })
            _write_state(state_path, latest_state_path, {
                **state_base, "last_step": script_name, "steps": steps,
            })
            continue

        step_started = _now_iso()
        _append_log(log_path, f"\n--- {script_name} ---\n")
        _write_state(state_path, latest_state_path, {
            **state_base, "last_step": script_name, "steps": steps,
        })

        try:
            result = subprocess.run(
                ["bash", script_name],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                timeout=_SCRIPT_TIMEOUT_SECONDS,
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


# ── Main pipeline ────────────────────────────────────────────────────────────


def _do_sandbox(project_id: str, project_root: Path, sandbox_id: str) -> int:
    base_dir = _sandbox_base_dir()
    sandbox_dir = base_dir / sandbox_id
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    state_path = sandbox_dir / "state.json"
    log_path = sandbox_dir / "run.log"
    worktree_path = sandbox_dir / "worktree"
    latest_state_path = _latest_state_path(project_id)

    started_at = _now_iso()
    state_base = {
        "state": "running",
        "sandbox_id": sandbox_id,
        "project_id": project_id,
        "started_at": started_at,
        "finished_at": None,
        "error": None,
        "last_step": "worktree",
        "steps": [],
    }
    _write_state(state_path, latest_state_path, state_base)
    _append_log(log_path, f"=== sandbox {sandbox_id} started {started_at} ===\n")
    _append_log(log_path, f"project_root: {project_root}\n")
    _append_log(log_path, f"runtime_root: {_runtime_root()}\n")
    _append_log(log_path, f"sandbox_dir: {sandbox_dir}\n")

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
            worktree_path, state_path, latest_state_path, log_path, state_base
        )

        finished_at = _now_iso()
        _write_state(state_path, latest_state_path, {
            **state_base,
            "state": "success" if success else "failed",
            "finished_at": finished_at,
            "error": error,
            "last_step": steps[-1]["name"] if steps else state_base["last_step"],
            "steps": steps,
        })
        outcome = "completed" if success else "failed"
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Host-side sandbox validation worker"
    )
    parser.add_argument("--project-root", required=True,
                        help="Host filesystem path to the project (already mapped)")
    parser.add_argument("--project-id", required=True,
                        help="Project identifier used to locate state/log files")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    project_root = Path(args.project_root).expanduser().resolve()
    project_id = args.project_id
    sandbox_id = _make_sandbox_id(project_id)

    logger.info(
        "sandbox worker start project_id=%s project_root=%s sandbox_id=%s runtime_root=%s",
        project_id, project_root, sandbox_id, _runtime_root(),
    )

    rc = _do_sandbox(project_id, project_root, sandbox_id)
    sys.exit(rc)


if __name__ == "__main__":
    main()
