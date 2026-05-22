from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

from ..models.schemas import ActionResult, SandboxValidationState, SandboxValidationStep

logger = logging.getLogger("control-api")

_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()

_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]

# Hard upper bounds. ``git worktree add`` should usually return in <2s on a
# warm repo; 60s is a generous safety net. The validator caller can override
# the worktree timeout via ``AI_DEV_FACTORY_SANDBOX_WORKTREE_TIMEOUT`` if a
# project genuinely needs more.
_WORKTREE_TIMEOUT_SECONDS = int(
    os.environ.get("AI_DEV_FACTORY_SANDBOX_WORKTREE_TIMEOUT", "60")
)
_GIT_LIST_TIMEOUT_SECONDS = 15
_GIT_PRUNE_TIMEOUT_SECONDS = 30
_GIT_REMOVE_TIMEOUT_SECONDS = 30


def _get_lock(project_id: str) -> threading.Lock:
    with _locks_mutex:
        if project_id not in _locks:
            _locks[project_id] = threading.Lock()
        return _locks[project_id]


def _sandbox_base_dir(project_root: Path) -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        p = Path(runtime_root) / "sandboxes"
    else:
        p = project_root / ".ai-dev-factory" / "sandboxes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_sandbox_id(project_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{project_id}-{ts}"


def _read_latest_sandbox_id(project_root: Path) -> str | None:
    p = _sandbox_base_dir(project_root) / "latest"
    if p.exists():
        return p.read_text(encoding="utf-8").strip() or None
    return None


def _write_latest_sandbox_id(project_root: Path, sandbox_id: str) -> None:
    p = _sandbox_base_dir(project_root) / "latest"
    p.write_text(sandbox_id, encoding="utf-8")


def _read_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"state": "idle"}


def _write_state(state_path: Path, data: dict) -> None:
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _append_log(log_path: Path, text: str) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text)


def _run_scripts(
    worktree_path: Path, state_path: Path, log_path: Path, state_base: dict
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
            _write_state(state_path, {**state_base, "last_step": script_name, "steps": steps})
            continue

        step_started = _now_iso()
        _append_log(log_path, f"\n--- {script_name} ---\n")
        _write_state(state_path, {**state_base, "last_step": script_name, "steps": steps})

        try:
            result = subprocess.run(
                ["bash", script_name],
                capture_output=True,
                text=True,
                cwd=str(worktree_path),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            step = {
                "name": script_name, "status": "failed", "exit_code": -1,
                "started_at": step_started, "finished_at": _now_iso(),
            }
            steps.append(step)
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
        _write_state(state_path, {**state_base, "last_step": script_name, "steps": steps})

        if result.returncode != 0:
            return False, f"{script_name} failed (exit {result.returncode})", steps

    return True, None, steps


# ── Worktree lifecycle helpers ────────────────────────────────────────────────


def _run_git(
    args: list[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
) -> tuple[int, str, str]:
    """Run ``git <args>`` with full safety:

    * ``stdin=DEVNULL``        — never blocks on an interactive credential prompt.
    * ``start_new_session=True`` — gives every git child its own process group so we
      can ``killpg`` the whole tree if it exceeds the timeout.
    * ``Popen.communicate(timeout=...)`` — kills the process group on timeout
      (`subprocess.run` alone may hang in cleanup when grandchildren keep
      pipes open).
    * Full stderr/stdout captured AND tee'd to the run log so the dashboard
      shows what actually happened even if the call hangs/explodes.

    Returns ``(returncode, stdout, stderr)``. Raises ``subprocess.TimeoutExpired``
    only after the process group has been killed.
    """
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
        # Kill the whole process group so grandchildren (hooks, signing
        # helpers, …) don't keep the pipes open and re-hang communicate().
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
    """Bail out fast with a clear message before launching ``git worktree add``.

    Returns ``None`` if all checks pass, otherwise an operator-readable
    error string. We intentionally check (and try to repair) the cases
    that previously caused the runner to hang forever: missing ``git``
    binary, non-git project_root, stale registration, leftover index
    lock, and a worktree directory left behind by a previous failure.
    """
    if shutil.which("git") is None:
        return "git binary not found in PATH"

    if not project_root.exists():
        return f"project_root does not exist: {project_root}"

    git_dir = project_root / ".git"
    if not git_dir.exists():
        return f"project_root is not a git repository (no .git): {project_root}"

    # `.git` can be a file (worktree) or a dir (regular repo); the lock
    # location lives inside the resolved gitdir.
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
        # Try to deregister + remove. If that fails we give up rather
        # than overwriting unknown state.
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
            # The directory may be untracked by git (stale leftover);
            # delete it directly so `worktree add` has a clean slot.
            try:
                shutil.rmtree(worktree_path)
                _append_log(log_path, f"removed stale dir: {worktree_path}\n")
            except OSError as e:
                return (
                    f"worktree path {worktree_path} could not be cleaned: "
                    f"git remove rc={rc} stderr={err.strip()[:200]} "
                    f"rmtree={e}"
                )

    # Prune stale registrations regardless. This is cheap and stops the
    # next `worktree add` from refusing because of a dangling pointer.
    try:
        _run_git(
            ["worktree", "prune"],
            cwd=project_root,
            log_path=log_path,
            timeout=_GIT_PRUNE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        # Non-fatal: log and continue. The subsequent `worktree add` is
        # what we ultimately care about.
        _append_log(log_path, "git worktree prune timed out (continuing)\n")

    return None


def _create_worktree(
    project_root: Path,
    worktree_path: Path,
    log_path: Path,
) -> tuple[bool, str | None]:
    """Run preflight + ``git worktree add``. Returns ``(ok, error_message)``.

    All exit paths leave a useful trace in ``log_path``. Never raises.
    """
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
        # E.g. git binary disappeared between preflight and exec, or PATH
        # changed. We still want a deterministic failure, not a hang.
        return False, f"git worktree add could not run: {e}"

    if rc != 0:
        return False, (
            f"git worktree add exited {rc}: {stderr.strip()[:500] or '<no stderr>'}"
        )

    _append_log(log_path, "worktree created\n")
    return True, None


# ── Main pipeline ─────────────────────────────────────────────────────────────


def _do_sandbox(project_id: str, project_root: Path, sandbox_id: str) -> None:
    base_dir = _sandbox_base_dir(project_root)
    sandbox_dir = base_dir / sandbox_id
    state_path = sandbox_dir / "state.json"
    log_path = sandbox_dir / "run.log"
    worktree_path = sandbox_dir / "worktree"

    started_at = _now_iso()
    state_base = {
        "state": "running",
        "sandbox_id": sandbox_id,
        "started_at": started_at,
        "finished_at": None,
        "error": None,
        "last_step": "worktree",
        "steps": [],
    }
    _write_state(state_path, state_base)
    _append_log(log_path, f"=== sandbox {sandbox_id} started {started_at} ===\n")
    _append_log(log_path, f"project_root: {project_root}\n")

    # The outer try/except guarantees the state file is finalised with
    # ``state=failed`` even if something explodes outside the per-step
    # handlers (e.g. disk full, permission error, KeyboardInterrupt
    # propagation, …). The dashboard must never observe an indefinite
    # ``state=running`` because the runner thread died silently.
    try:
        ok, error = _create_worktree(project_root, worktree_path, log_path)
        if not ok:
            _append_log(log_path, f"worktree creation failed: {error}\n")
            _write_state(
                state_path,
                {
                    **state_base,
                    "state": "failed",
                    "finished_at": _now_iso(),
                    "error": error,
                },
            )
            return

        success, error, steps = _run_scripts(
            worktree_path, state_path, log_path, state_base
        )

        finished_at = _now_iso()
        _write_state(state_path, {
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
    except Exception as e:  # noqa: BLE001 — catch-all is intentional
        tb = traceback.format_exc()
        logger.exception(
            "sandbox: unhandled error during _do_sandbox project=%s sandbox=%s",
            project_id,
            sandbox_id,
        )
        _append_log(log_path, f"\nunhandled exception: {e}\n{tb}\n")
        _write_state(
            state_path,
            {
                **state_base,
                "state": "failed",
                "finished_at": _now_iso(),
                "error": f"unhandled exception in sandbox runner: {e}",
            },
        )


def _sandbox_thread(
    project_id: str, project_root: Path, sandbox_id: str, lock: threading.Lock
) -> None:
    # The thread wrapper is now a thin shell. ``_do_sandbox`` is responsible
    # for finalising state on any error path; we just guarantee the lock
    # is released so the next start_sandbox_validation() can run.
    try:
        _do_sandbox(project_id, project_root, sandbox_id)
    except Exception:
        # _do_sandbox catches its own; this guard is belt-and-suspenders
        # in case a future refactor moves work outside its try-block.
        logger.exception(
            "sandbox: top-level error project=%s sandbox=%s", project_id, sandbox_id
        )
    finally:
        lock.release()


def start_sandbox_validation(project_id: str, project_root: Path) -> ActionResult:
    lock = _get_lock(project_id)
    if not lock.acquire(blocking=False):
        return ActionResult(ok=False, message="sandbox already running", error="locked")

    sandbox_id = _make_sandbox_id(project_id)
    base_dir = _sandbox_base_dir(project_root)
    sandbox_dir = base_dir / sandbox_id
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    state_path = sandbox_dir / "state.json"
    _write_state(state_path, {
        "state": "pending",
        "sandbox_id": sandbox_id,
        "started_at": _now_iso(),
        "finished_at": None,
        "error": None,
        "last_step": None,
        "steps": [],
    })
    _write_latest_sandbox_id(project_root, sandbox_id)

    t = threading.Thread(
        target=_sandbox_thread,
        args=(project_id, project_root, sandbox_id, lock),
        daemon=True,
    )
    t.start()
    return ActionResult(ok=True, message="sandbox validation started")


def get_sandbox_state(project_root: Path) -> SandboxValidationState:
    sandbox_id = _read_latest_sandbox_id(project_root)
    if sandbox_id is None:
        return SandboxValidationState(state="idle")

    base_dir = _sandbox_base_dir(project_root)
    state_path = base_dir / sandbox_id / "state.json"
    raw = _read_state(state_path)

    steps = [
        SandboxValidationStep(
            name=s["name"],
            status=s["status"],
            exit_code=s.get("exit_code"),
            started_at=s.get("started_at"),
            finished_at=s.get("finished_at"),
        )
        for s in raw.get("steps", [])
    ]
    return SandboxValidationState(
        state=raw.get("state", "idle"),
        sandbox_id=raw.get("sandbox_id"),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
        error=raw.get("error"),
        last_step=raw.get("last_step"),
        steps=steps,
    )


def get_sandbox_logs(project_root: Path, lines: int) -> list[str]:
    sandbox_id = _read_latest_sandbox_id(project_root)
    if sandbox_id is None:
        return []

    log_path = _sandbox_base_dir(project_root) / sandbox_id / "run.log"
    if not log_path.exists():
        return []

    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return all_lines[-lines:] if len(all_lines) > lines else all_lines
