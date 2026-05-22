from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..models.schemas import ActionResult, SandboxValidationState, SandboxValidationStep

logger = logging.getLogger("control-api")

_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()

_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]


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

    _append_log(log_path, "\n--- creating git worktree ---\n")
    try:
        wt_result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        msg = "git worktree creation timed out"
        _append_log(log_path, f"{msg}\n")
        _write_state(state_path, {**state_base, "state": "failed", "finished_at": _now_iso(), "error": msg})
        return

    if wt_result.stdout:
        _append_log(log_path, wt_result.stdout)
    if wt_result.stderr:
        _append_log(log_path, wt_result.stderr)

    if wt_result.returncode != 0:
        msg = f"git worktree failed (exit {wt_result.returncode}): {wt_result.stderr.strip()[:200]}"
        _append_log(log_path, f"{msg}\n")
        _write_state(state_path, {**state_base, "state": "failed", "finished_at": _now_iso(), "error": msg})
        return

    _append_log(log_path, "worktree created\n")

    success, error, steps = _run_scripts(worktree_path, state_path, log_path, state_base)

    finished_at = _now_iso()
    _write_state(state_path, {
        **state_base,
        "state": "success" if success else "failed",
        "finished_at": finished_at,
        "error": error,
        "last_step": steps[-1]["name"] if steps else None,
        "steps": steps,
    })
    outcome = "completed" if success else "failed"
    _append_log(log_path, f"\n=== sandbox {sandbox_id} {outcome} {finished_at} ===\n")


def _sandbox_thread(project_id: str, project_root: Path, sandbox_id: str, lock: threading.Lock) -> None:
    try:
        _do_sandbox(project_id, project_root, sandbox_id)
    except Exception as e:
        logger.exception("sandbox: unhandled error for %s: %s", project_id, e)
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
