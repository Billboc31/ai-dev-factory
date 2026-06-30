#!/usr/bin/env python3
"""Local workflow daemon for ai-dev-factory.

Polls runs/*/state.json and launches run_ticket.py --auto for auto-runnable states.
Never bypasses human gate states.
"""

from __future__ import annotations

import argparse
import datetime
import errno
import fcntl
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


# In-memory handles for background worker processes (not serializable to JSON).
_ACTIVE_WORKERS: dict[str, dict] = {}

# Max intelligence/readiness tickets processed per daemon cycle once workers are async.
_PIPELINE_TICKETS_PER_CYCLE = 32

# Suppress .pyc generation for this process *and* every subprocess we spawn.
# `.pyc` files in __pycache__/ are the #1 source of runtime dirty trees that
# block daemon sync/rebase, and they leak into worktrees that are otherwise
# expected to stay clean.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parent
# Location of the factory scripts (ai-dev-factory clone). Managed-project daemons
# must NOT use this for git operations — see ``_resolve_repo_root`` in ``main()``.
_SCRIPT_REPO_ROOT = ROOT.parent.parent
REPO_ROOT = _SCRIPT_REPO_ROOT
RUN_TICKET = ROOT / "run_ticket.py"
RUN_ISSUE_INTAKE = ROOT / "run_issue_intake.py"
RUN_ISSUE_MAPPER = ROOT / "run_issue_mapper.py"
ISSUE_INDEX_FILENAME = ".issue-intake.json"
PROJECT_MAP_FILENAME = ".project-map.json"
RETRY_STATE_FILENAME = "retry-state.json"
WORKERS_REGISTRY_FILENAME = "workers.json"
DEFAULT_WORKTREES_DIR = _SCRIPT_REPO_ROOT.parent / (_SCRIPT_REPO_ROOT.name + "-worktrees")

_LOG_FILE: "Path | None" = None

_wm_spec = importlib.util.spec_from_file_location("_worktree_manager", ROOT / "worktree_manager.py")
_wm_mod = importlib.util.module_from_spec(_wm_spec)  # type: ignore[arg-type]
_wm_spec.loader.exec_module(_wm_mod)  # type: ignore[union-attr]
create_ticket_worktree = _wm_mod.create_ticket_worktree
create_ticket_branch_and_worktree = _wm_mod.create_ticket_branch_and_worktree
fetch_origin_main = _wm_mod.fetch_origin_main
cleanup_failed_intake = _wm_mod.cleanup_failed_intake
get_ticket_worktree_path = _wm_mod.get_ticket_worktree_path
remove_ticket_worktree = _wm_mod.remove_ticket_worktree
del _wm_spec, _wm_mod

_rc_spec = importlib.util.spec_from_file_location("_runtime_checkpoint", ROOT / "runtime_checkpoint.py")
_rc_mod = importlib.util.module_from_spec(_rc_spec)  # type: ignore[arg-type]
_rc_spec.loader.exec_module(_rc_mod)  # type: ignore[union-attr]
checkpoint_transition = _rc_mod.checkpoint_transition
CheckpointError = _rc_mod.CheckpointError
DirtyTreeError = _rc_mod.DirtyTreeError
is_runtime_ignored_path = _rc_mod.is_runtime_ignored_path
classify_intake_dirty_paths = _rc_mod.classify_intake_dirty_paths
parse_porcelain_paths = _rc_mod.parse_porcelain_paths
del _rc_spec, _rc_mod


def _no_bytecode_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``os.environ`` with ``PYTHONDONTWRITEBYTECODE=1`` forced.

    Used for every subprocess this daemon spawns (planner, coder, reviewer,
    tester, run_ticket workers, issue intake, …) so they never write ``.pyc``
    files into the worktree and salt the working tree between cycles.
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env

_rdb_spec = importlib.util.spec_from_file_location("_runtime_db", ROOT / "runtime_db.py")
_rdb_mod = importlib.util.module_from_spec(_rdb_spec)  # type: ignore[arg-type]
_rdb_spec.loader.exec_module(_rdb_mod)  # type: ignore[union-attr]
_rdb_get_db_path = _rdb_mod.get_db_path
_rdb_init = _rdb_mod.init_runtime_db
_rdb_check_and_recover = _rdb_mod.check_and_recover_db
_rdb_record_intake = _rdb_mod.record_issue_intake
_rdb_list_intake = _rdb_mod.list_issue_intake
_rdb_upsert_ticket = _rdb_mod.upsert_ticket_runtime
_rdb_upsert_worker = _rdb_mod.upsert_worker
_rdb_remove_worker = _rdb_mod.remove_worker
_rdb_list_workers = _rdb_mod.list_workers
_rdb_list_backlog_batches = _rdb_mod.list_backlog_batches
_rdb_get_ticket_readiness = _rdb_mod.get_ticket_readiness
_rdb_get_ticket_runtime = _rdb_mod.get_ticket_runtime
del _rdb_spec, _rdb_mod

_rr_spec = importlib.util.spec_from_file_location(
    "_runtime_resolver",
    REPO_ROOT / "services" / "control_api" / "services" / "runtime_resolver.py",
)
_rr_mod = importlib.util.module_from_spec(_rr_spec)  # type: ignore[arg-type]
_rr_spec.loader.exec_module(_rr_mod)  # type: ignore[union-attr]
_rr_resolve_state_dir = _rr_mod.resolve_state_dir
_rr_resolve_logs_dir = _rr_mod.resolve_logs_dir
del _rr_spec, _rr_mod

_td_spec = importlib.util.spec_from_file_location("_ticket_dispatcher", ROOT / "ticket_dispatcher.py")
_td_mod = importlib.util.module_from_spec(_td_spec)  # type: ignore[arg-type]
_td_spec.loader.exec_module(_td_mod)  # type: ignore[union-attr]
_get_dispatcher_mode = _td_mod.get_dispatcher_mode
_get_recommended_tickets = _td_mod.get_recommended_tickets
del _td_spec, _td_mod

_tp_spec = importlib.util.spec_from_file_location("_ticket_pipeline", ROOT / "ticket_pipeline.py")
_tp_mod = importlib.util.module_from_spec(_tp_spec)  # type: ignore[arg-type]
_tp_spec.loader.exec_module(_tp_mod)  # type: ignore[union-attr]
_is_auto_pipeline_enabled = _tp_mod.is_auto_pipeline_enabled
_find_next_pipeline_ticket = _tp_mod.find_next_ticket
_process_ticket_pipeline = _tp_mod.process_ticket
del _tp_spec, _tp_mod

_te_spec = importlib.util.spec_from_file_location(
    "_ticket_execution_eligibility", ROOT / "ticket_execution_eligibility.py",
)
_te_mod = importlib.util.module_from_spec(_te_spec)  # type: ignore[arg-type]
_te_spec.loader.exec_module(_te_mod)  # type: ignore[union-attr]
_evaluate_eligibility = _te_mod.evaluate_eligibility
del _te_spec, _te_mod

_bb_spec = importlib.util.spec_from_file_location("_backlog_batch", ROOT / "backlog_batch.py")
_bb_mod = importlib.util.module_from_spec(_bb_spec)  # type: ignore[arg-type]
sys.modules["_backlog_batch"] = _bb_mod
_bb_spec.loader.exec_module(_bb_mod)  # type: ignore[union-attr]
_backlog_batch = _bb_mod
del _bb_spec, _bb_mod

_gda_spec = importlib.util.spec_from_file_location(
    "_global_dependency_analyzer", ROOT / "global_dependency_analyzer.py",
)
_gda_mod = importlib.util.module_from_spec(_gda_spec)  # type: ignore[arg-type]
sys.modules["_global_dependency_analyzer"] = _gda_mod
_gda_spec.loader.exec_module(_gda_mod)  # type: ignore[union-attr]
_global_dependency_analyzer = _gda_mod
del _gda_spec, _gda_mod

_rs_spec = importlib.util.spec_from_file_location("_runtime_settings", ROOT / "runtime_settings.py")
_rs_mod = importlib.util.module_from_spec(_rs_spec)  # type: ignore[arg-type]
sys.modules["_runtime_settings"] = _rs_mod
_rs_spec.loader.exec_module(_rs_mod)  # type: ignore[union-attr]
_runtime_settings = _rs_mod
del _rs_spec, _rs_mod

# SQLite path and init are cached so _rdb_get_db_path() (subprocess) runs only once per daemon process.
_DB_PATH_RESOLVED: bool = False
_DB_PATH_VALUE: "Path | None" = None
_DB_INITIALIZED: bool = False

# Singleton guard — file handle kept open for process lifetime so the exclusive lock holds.
_SINGLETON_LOCK_FH = None


def _cached_db_path() -> "Path | None":
    global _DB_PATH_RESOLVED, _DB_PATH_VALUE
    if not _DB_PATH_RESOLVED:
        _DB_PATH_VALUE = _rdb_get_db_path()
        _DB_PATH_RESOLVED = True
    return _DB_PATH_VALUE


def _ensure_db() -> "Path | None":
    """Return an initialized DB path, resolving and initialising at most once per process."""
    global _DB_INITIALIZED
    db_path = _cached_db_path()
    if not db_path:
        return None
    if not _DB_INITIALIZED:
        try:
            _rdb_check_and_recover(db_path)
            _rdb_init(db_path)
            _DB_INITIALIZED = True
        except Exception as exc:
            _log(f"SQLite init failed: {exc}")
            return None
    return db_path


def _acquire_daemon_singleton(lock_dir: Path) -> bool:
    """Acquire a process-lifetime LOCK_EX|LOCK_NB on daemon-singleton.lock.

    Returns False immediately if another daemon process already holds the lock,
    so the caller can exit cleanly instead of racing on SQLite.
    """
    global _SINGLETON_LOCK_FH
    lock_path = lock_dir / "daemon-singleton.lock"
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(lock_path, "w")
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(json.dumps({"pid": os.getpid(), "started_at": _now_iso()}) + "\n")
        fh.flush()
        _SINGLETON_LOCK_FH = fh  # keep open so lock holds for process lifetime
        return True
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            return False
        # Cannot determine — proceed rather than refusing to start
        _log(f"daemon singleton lock warning: {exc}")
        return True

AUTO_RUNNABLE_STATES = frozenset({
    "INIT",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_APPROVED",
    "PLAN_FIX_REQUIRED",
    "IMPLEMENTATION_FIX_REQUIRED",
})

HUMAN_GATE_STATES = frozenset({
    "PLAN_REVIEW_NEEDED",
    "TEST_COMPLETE",
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
})

# Retry/cooldown policies per failure class.
# Keys match the categories produced by classify_runtime_failure in run_step.py.
_RETRY_POLICIES: dict[str, dict] = {
    "quota_exceeded":          {"action": "cooldown",    "cooldown_seconds": 3600},
    "provider_error":          {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_crashed":         {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_failed":          {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    "empty_output":            {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    # planner_invalid: model produced a structurally bad plan. Bounded retries
    # with a short delay — usually the next sample is fine; otherwise stop so
    # a human can refine the prompt.
    "planner_invalid":         {"action": "fixed_delay", "delay_seconds": 120, "max_retries": 3},
    # dirty_tree: a previous step left runs/<ticket>/ uncommitted. Bounded
    # retries with a very short delay — the next cycle's auto-checkpoint or
    # human intervention should clear it; otherwise stop.
    "dirty_tree":              {"action": "fixed_delay", "delay_seconds": 60,  "max_retries": 3},
    "write_permission_missing": {"action": "stop"},
    "unknown":                 {"action": "stop"},
}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(message: str) -> None:
    """Log one daemon line.

    Avoids the historical "every line written twice" issue that the
    dashboard logs surfaced: when the daemon is spawned by
    ``daemon_manager.start`` its ``stdout`` is already redirected to
    ``daemon.log`` via Popen. Mirroring the same line into ``_LOG_FILE``
    (which resolves to the same path) would double every entry.

    Rule:
      - always ``print(line)`` — captured by the parent's redirection or
        shown on the terminal when running interactively;
      - mirror to ``_LOG_FILE`` *only* in interactive mode (TTY stdout).
    """
    line = f"[{_now_iso()}] [daemon] {message}"
    print(line, flush=True)
    if _LOG_FILE and sys.stdout.isatty():
        try:
            with _LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def _lock_path(run_dir: Path) -> Path:
    return run_dir / "daemon.lock"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(run_dir: Path) -> bool:
    """Try to acquire daemon.lock. Returns True if acquired, False if held by a live process."""
    lock = _lock_path(run_dir)
    if lock.exists():
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if isinstance(pid, int) and _is_pid_alive(pid):
                return False
            _log(f"cleaning stale lock for {run_dir.name} (pid={pid})")
            lock.unlink()
        except (json.JSONDecodeError, OSError):
            try:
                lock.unlink()
            except OSError:
                pass
    try:
        lock.write_text(
            json.dumps({"pid": os.getpid(), "created_at": _now_iso()}),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def _release_lock(run_dir: Path) -> None:
    try:
        _lock_path(run_dir).unlink()
    except OSError:
        pass


def _set_lock_holder_pid(run_dir: Path, pid: int) -> None:
    """Rewrite daemon.lock so stale detection tracks the worker child PID."""
    try:
        _lock_path(run_dir).write_text(
            json.dumps({"pid": pid, "created_at": _now_iso()}),
            encoding="utf-8",
        )
    except OSError:
        pass


# ── retry / cooldown state ────────────────────────────────────────────────────

def _retry_state_path(run_dir: Path) -> Path:
    return run_dir / RETRY_STATE_FILENAME


def _load_retry_state(run_dir: Path) -> dict:
    path = _retry_state_path(run_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_retry_state(run_dir: Path, state: dict) -> None:
    path = _retry_state_path(run_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _clear_retry_state(run_dir: Path) -> None:
    try:
        _retry_state_path(run_dir).unlink()
    except OSError:
        pass


# ── workers registry ──────────────────────────────────────────────────────────

def _workers_registry_path(state_dir: Path) -> Path:
    return state_dir / WORKERS_REGISTRY_FILENAME


def _load_workers_registry(state_dir: Path) -> dict:
    path = _workers_registry_path(state_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_workers_registry(state_dir: Path, workers: dict) -> None:
    path = _workers_registry_path(state_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(workers, indent=2), encoding="utf-8")
    tmp.replace(path)


def _register_worker(
    state_dir: Path,
    ticket_id: str,
    branch: str | None,
    worktree_path: str,
    *,
    pid: int,
) -> None:
    workers = _load_workers_registry(state_dir)
    workers[ticket_id] = {
        "pid": pid,
        "branch": branch,
        "worktree_path": worktree_path,
        "started_at": _now_iso(),
    }
    _save_workers_registry(state_dir, workers)
    db_path = _ensure_db()
    if db_path:
        try:
            _rdb_upsert_worker(db_path, ticket_id, pid, branch, worktree_path)
        except Exception as exc:
            _log(f"SQLite worker register failed for {ticket_id}: {exc}")


def _unregister_worker(state_dir: Path, ticket_id: str) -> None:
    workers = _load_workers_registry(state_dir)
    workers.pop(ticket_id, None)
    _save_workers_registry(state_dir, workers)
    db_path = _cached_db_path()
    if db_path and db_path.exists():
        try:
            _rdb_remove_worker(db_path, ticket_id)
        except Exception as exc:
            _log(f"SQLite worker unregister failed for {ticket_id}: {exc}")


def _cleanup_stale_workers(state_dir: Path) -> None:
    """Remove dead PIDs from workers.json and SQLite — called at daemon startup."""
    workers = _load_workers_registry(state_dir)
    stale: list[str] = []
    if workers:
        stale = [
            tid for tid, w in workers.items()
            if not isinstance(w.get("pid"), int) or not _is_pid_alive(w["pid"])
        ]
        if stale:
            for tid in stale:
                _log(f"removing stale worker entry for {tid} (pid={workers[tid].get('pid')} dead)")
                del workers[tid]
            _save_workers_registry(state_dir, workers)

    db_path = _cached_db_path()
    if not db_path or not db_path.exists():
        return
    try:
        db_workers = _rdb_list_workers(db_path)
        for w in db_workers:
            tid = w["ticket_id"]
            pid = w.get("pid")
            if not isinstance(pid, int) or not _is_pid_alive(pid):
                if tid not in stale:
                    _log(f"removing stale SQLite worker entry for {tid} (pid={pid} dead)")
                _rdb_remove_worker(db_path, tid)
    except Exception as exc:
        _log(f"SQLite stale worker cleanup failed: {exc}")


def _count_live_workers(state_dir: Path) -> int:
    """Return the number of registered workers whose PID is still alive."""
    workers = _load_workers_registry(state_dir)
    live = 0
    for w in workers.values():
        pid = w.get("pid")
        if isinstance(pid, int) and _is_pid_alive(pid):
            live += 1
    return live


def _handle_worker_exit(
    ticket_id: str,
    run_dir: Path,
    returncode: int,
) -> None:
    if returncode != 0:
        failure_class = _read_last_failure_class(run_dir)
        if failure_class:
            retry_state = _load_retry_state(run_dir)
            retry_state = _apply_retry_policy(ticket_id, failure_class, retry_state)
            _save_retry_state(run_dir, retry_state)
        else:
            _log(f"{ticket_id}: no failure class in runtime.log — retry policy not applied")
    else:
        _clear_retry_state(run_dir)


def reap_completed_workers(state_dir: Path) -> None:
    """Reap background run_ticket workers and release their locks."""
    for ticket_id in list(_ACTIVE_WORKERS.keys()):
        info = _ACTIVE_WORKERS[ticket_id]
        proc = info["proc"]
        returncode = proc.poll()
        if returncode is None:
            continue
        run_dir = info["run_dir"]
        _log(f"{ticket_id}: worker exited rc={returncode}")
        _handle_worker_exit(ticket_id, run_dir, returncode)
        _unregister_worker(state_dir, ticket_id)
        _release_lock(run_dir)
        del _ACTIVE_WORKERS[ticket_id]


def _read_last_failure_class(run_dir: Path) -> str | None:
    """Return the last failure class logged in runtime.log, or None."""
    log_path = run_dir / "runtime.log"
    if not log_path.exists():
        return None
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return None
    last_class = None
    for line in content.splitlines():
        m = re.search(r"runtime failure: (\w+)", line)
        if m:
            last_class = m.group(1)
    return last_class


def _cooldown_until(seconds: int) -> str:
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply_retry_policy(ticket_id: str, failure_class: str, retry_state: dict) -> dict:
    """Return an updated retry_state dict after applying the policy for failure_class."""
    policy = _RETRY_POLICIES.get(failure_class, {"action": "stop"})
    action = policy["action"]
    new_state: dict = dict(retry_state)
    new_state["failure_class"] = failure_class
    new_state.setdefault("retry_count", 0)

    if action == "stop":
        new_state["stopped"] = True
        new_state["stop_reason"] = failure_class
        _log(f"{ticket_id}: retry policy=stop failure={failure_class} — requires human attention")

    elif action == "cooldown":
        seconds = policy["cooldown_seconds"]
        new_state["cooldown_until"] = _cooldown_until(seconds)
        new_state.pop("stopped", None)
        _log(f"{ticket_id}: retry policy=cooldown failure={failure_class} cooldown={seconds}s until={new_state['cooldown_until']}")

    elif action == "exponential":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            fallback = policy["fallback_cooldown_seconds"]
            new_state["cooldown_until"] = _cooldown_until(fallback)
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} max_retries={max_retries} reached — cooldown {fallback}s")
        else:
            delay = policy["base_seconds"] * (2 ** count)
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    elif action == "fixed_delay":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            new_state["stopped"] = True
            new_state["stop_reason"] = f"{failure_class}_max_retries"
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} max_retries={max_retries} reached — stopped")
        else:
            delay = policy["delay_seconds"]
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    return new_state


def _is_blocked_by_retry(ticket_id: str, retry_state: dict) -> bool:
    """Return True and log if the ticket must be skipped due to retry/cooldown state."""
    if retry_state.get("stopped"):
        reason = retry_state.get("stop_reason", "unknown")
        _log(f"skipping {ticket_id}: stopped reason={reason} — requires human attention")
        return True
    cooldown_until = retry_state.get("cooldown_until")
    if cooldown_until:
        try:
            until_dt = datetime.datetime.strptime(cooldown_until, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < until_dt:
                remaining = int((until_dt - now).total_seconds())
                _log(f"skipping {ticket_id}: in cooldown until={cooldown_until} remaining={remaining}s")
                return True
        except ValueError:
            pass
    return False


# ── pre-flight dirty tree check ───────────────────────────────────────────────

# Mirrors COMMIT_SCOPE in run_ticket.py — files in these paths are auto-checkpointable
_CODE_SCOPE_PREFIXES: tuple[str, ...] = (
    "tools/",
    "tests/",
    "prompts/",
    "tickets/",
    "docs/",
    "ai/",
    "services/",
    "apps/",
    "README.md",
    ".gitignore",
    "package.json",
    "package-lock.json",
)


def _classify_dirty_files(ticket_id: str) -> tuple[list[str], list[str], list[str]]:
    """Run git status and classify dirty files into three buckets.

    Returns (workflow_artifacts, code_scope_files, unknown_files).
    - workflow_artifacts: files under runs/ — auto-checkpointable
    - code_scope_files: files in COMMIT_SCOPE — auto-checkpointable with --include-code
    - unknown_files: anything else — trigger safe abort
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    workflow_artifacts: list[str] = []
    code_scope_files: list[str] = []
    unknown_files: list[str] = []
    if result.returncode != 0:
        return workflow_artifacts, code_scope_files, unknown_files
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if path.startswith("runs/"):
            workflow_artifacts.append(path)
        elif any(path.startswith(p) for p in _CODE_SCOPE_PREFIXES):
            code_scope_files.append(path)
        else:
            unknown_files.append(path)
    return workflow_artifacts, code_scope_files, unknown_files


def _ensure_clean_working_tree(ticket_id: str, auto_push: bool = False) -> bool:
    """Ensure working tree is clean before launching a ticket step.

    If dirty files are workflow artifacts or code-scope files → automatic checkpoint commit.
    If any unknown files are dirty → abort safely.
    Returns True if ready to proceed, False to abort.
    """
    workflow_artifacts, code_scope_files, unknown_files = _classify_dirty_files(ticket_id)

    if not workflow_artifacts and not code_scope_files and not unknown_files:
        return True

    if unknown_files:
        _log(f"{ticket_id}: pre-flight abort — unknown dirty files: {unknown_files!r}")
        _log(f"{ticket_id}: pre-flight abort — commit or stash unknown files before daemon can proceed")
        return False

    if code_scope_files:
        _log(f"{ticket_id}: pre-flight — dirty code-scope files detected: {code_scope_files!r}")

    _log(f"{ticket_id}: pre-flight — triggering checkpoint_transition()")

    try:
        checkpoint_transition(
            ticket_id,
            f"{ticket_id}: pre-flight checkpoint — persist dirty runtime artifacts",
            push=auto_push,
            include_code=True,
        )

        _log(f"{ticket_id}: pre-flight checkpoint ok")
        return True

    except CheckpointError as exc:
        _log(f"{ticket_id}: pre-flight abort — checkpoint failed: {exc}")
        return False

    except DirtyTreeError as exc:
        _log(f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — pre-flight: {exc}")
        return False


# ── state json helpers ────────────────────────────────────────────────────────

def _load_state_json(run_dir: Path) -> dict:
    path = run_dir / "state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state_json(run_dir: Path, data: dict) -> None:
    path = run_dir / "state.json"
    updated = {**data, "updated_at": _now_iso()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    tmp.replace(path)


# ── PR lifecycle ──────────────────────────────────────────────────────────────

def _pr_title(ticket_id: str, run_dir: Path) -> str:
    ticket_path = run_dir / "ticket.md"
    if ticket_path.exists():
        for line in ticket_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return f"{ticket_id} — workflow complete"


def _pr_body(ticket_id: str, issue_number: int | None) -> str:
    lines = [
        f"## {ticket_id}",
        "",
        "Workflow reached `TEST_COMPLETE`.",
        "",
        "### Gates",
        "- [x] PLAN_APPROVED",
        "- [x] IMPLEMENTATION_APPROVED",
        "- [ ] MEMORY_APPROVED",
    ]
    if issue_number:
        lines += ["", f"Closes #{issue_number}"]
    return "\n".join(lines)


def create_or_update_pr(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Create or update the GitHub PR for a ticket at TEST_COMPLETE. Non-blocking on gh failure."""
    state = _load_state_json(run_dir)
    branch = state.get("branch")
    issue_number = state.get("issue_number")
    pr_number = state.get("pr_number")

    if not branch:
        _log(f"{ticket_id}: create_or_update_pr: no branch in state — skipping")
        return

    # Skip if PR body is already synced to avoid repeated gh pr edit calls
    if pr_number is not None and state.get("pr_synced"):
        return

    title = _pr_title(ticket_id, run_dir)
    body = _pr_body(ticket_id, issue_number)

    if pr_number is None:
        list_cmd = ["gh", "pr", "list", "--head", branch, "--json", "number", "--state", "open"]
        if repo:
            list_cmd += ["--repo", repo]
        try:
            list_result = subprocess.run(list_cmd, capture_output=True, text=True, check=False)
            if list_result.returncode == 0 and list_result.stdout.strip():
                existing = json.loads(list_result.stdout)
                if existing:
                    pr_number = existing[0]["number"]
                    _log(f"{ticket_id}: found existing PR #{pr_number} — will update")
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            _log(f"{ticket_id}: gh pr list failed — proceeding with create")

    if pr_number is None:
        # Fallback: branch may have been renamed — search open PRs by ticket_id prefix
        prefix = f"ticket/{ticket_id}-"
        fallback_cmd = ["gh", "pr", "list", "--state", "open", "--json", "number,headRefName", "--limit", "100"]
        if repo:
            fallback_cmd += ["--repo", repo]
        try:
            fb_result = subprocess.run(fallback_cmd, capture_output=True, text=True, check=False)
            if fb_result.returncode == 0 and fb_result.stdout.strip():
                all_prs = json.loads(fb_result.stdout)
                matching = [p for p in all_prs if isinstance(p, dict) and str(p.get("headRefName", "")).startswith(prefix)]
                if matching:
                    pr_number = matching[0]["number"]
                    head_ref = matching[0].get("headRefName", "")
                    _log(f"{ticket_id}: found PR #{pr_number} via branch prefix {prefix!r} (headRef={head_ref!r}) — branch may have been renamed")
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            pass

    if pr_number is not None:
        edit_cmd = ["gh", "pr", "edit", str(pr_number), "--body", body]
        if repo:
            edit_cmd += ["--repo", repo]
        try:
            result = subprocess.run(edit_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                state["pr_synced"] = True
                _save_state_json(run_dir, state)
                _log(f"{ticket_id}: PR #{pr_number} updated")
            else:
                _log(f"{ticket_id}: gh pr edit failed (rc={result.returncode}): {result.stderr.strip()}")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot update PR #{pr_number}")
    else:
        create_cmd = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        if repo:
            create_cmd += ["--repo", repo]
        try:
            result = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                m = re.search(r"/pull/(\d+)", pr_url)
                if m:
                    pr_number = int(m.group(1))
                    state["pr_number"] = pr_number
                    state["pr_synced"] = True
                    _save_state_json(run_dir, state)
                    _log(f"{ticket_id}: PR #{pr_number} created: {pr_url}")
                else:
                    _log(f"{ticket_id}: PR created but number not parsed from: {pr_url!r}")
            else:
                stderr = result.stderr.strip()
                _log(f"{ticket_id}: gh pr create failed (rc={result.returncode}): {stderr}")
                if "No commits between" in stderr:
                    state["pr_skipped_no_diff"] = True
                    state["daemon_archived"] = True
                    _save_state_json(run_dir, state)
                    _log(f"{ticket_id}: no diff — marked pr_skipped_no_diff=true daemon_archived=true")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot create PR")


def check_and_close_issue(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Detect merged PR, close the source issue, and remove ai-ready label. Non-blocking."""
    state = _load_state_json(run_dir)

    # Skip if already handled to avoid repeated gh calls on every daemon cycle
    if state.get("issue_closed"):
        return

    pr_number = state.get("pr_number")
    issue_number = state.get("issue_number")

    if not pr_number:
        return

    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "state"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"{ticket_id}: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
            return
        pr_data = json.loads(result.stdout)
    except (json.JSONDecodeError, FileNotFoundError):
        _log(f"{ticket_id}: gh pr view failed or gh not found")
        return

    if pr_data.get("state") != "MERGED":
        return

    _log(f"{ticket_id}: PR #{pr_number} merged — handling issue closure")

    if not issue_number:
        return

    close_cmd = ["gh", "issue", "close", str(issue_number)]
    if repo:
        close_cmd += ["--repo", repo]
    try:
        close_result = subprocess.run(close_cmd, capture_output=True, text=True, check=False)
        if close_result.returncode == 0:
            _log(f"{ticket_id}: issue #{issue_number} closed")
        else:
            _log(f"{ticket_id}: gh issue close failed (rc={close_result.returncode}): {close_result.stderr.strip()}")
    except FileNotFoundError:
        _log(f"{ticket_id}: gh not found — cannot close issue #{issue_number}")

    label_cmd = ["gh", "issue", "edit", str(issue_number), "--remove-label", "ai-ready"]
    if repo:
        label_cmd += ["--repo", repo]
    try:
        label_result = subprocess.run(label_cmd, capture_output=True, text=True, check=False)
        if label_result.returncode == 0:
            _log(f"{ticket_id}: label 'ai-ready' removed from issue #{issue_number}")
        else:
            _log(f"{ticket_id}: gh issue edit label failed (rc={label_result.returncode}): {label_result.stderr.strip()}")
    except FileNotFoundError:
        _log(f"{ticket_id}: gh not found — cannot remove label from issue #{issue_number}")

    # Persist so we don't repeat close/label-removal on subsequent daemon cycles
    state["issue_closed"] = True
    _save_state_json(run_dir, state)


def _checkpoint_and_push_before_pr(ticket_id: str, cwd: str | None = None) -> bool:
    """Checkpoint commit + push before PR creation. Returns False if commit or push failed."""
    _log(f"{ticket_id}: pre-PR checkpoint commit")
    try:
        checkpoint_transition(
            ticket_id,
            f"{ticket_id}: checkpoint [TEST_COMPLETE] — update workflow artifacts",
            push=True,
            include_code=True,
            cwd=cwd,
        )
        _log(f"{ticket_id}: pre-PR push ok")
        return True
    except CheckpointError as exc:
        _log(f"{ticket_id}: pre-PR checkpoint failed: {exc}")
        return False
    except DirtyTreeError as exc:
        _log(f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — pre-PR: {exc}")
        return False


def auto_merge_pr(ticket_id: str, run_dir: Path, repo: str | None) -> bool:
    """Merge the ticket PR automatically if all guards pass. Returns True if merged."""
    state = _load_state_json(run_dir)
    pr_number = state.get("pr_number")

    if not pr_number:
        _log(f"{ticket_id}: auto-merge: no pr_number in state — skipping")
        return False

    if state.get("pr_merged"):
        _log(f"{ticket_id}: auto-merge: already merged — skipping")
        return False

    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "state,mergeable"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"{ticket_id}: auto-merge: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
            return False
        pr_data = json.loads(result.stdout)
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False
    except json.JSONDecodeError:
        _log(f"{ticket_id}: auto-merge: invalid JSON from gh pr view")
        return False

    pr_state = pr_data.get("state")
    if pr_state == "MERGED":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} already merged — marking state")
        state["pr_merged"] = True
        state["daemon_archived"] = True
        _save_state_json(run_dir, state)
        return True
    if pr_state != "OPEN":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} state={pr_state!r} — not OPEN, skipping")
        return False

    mergeable = pr_data.get("mergeable")
    if mergeable == "CONFLICTING":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} has conflicts — skipping")
        return False

    merge_cmd = ["gh", "pr", "merge", str(pr_number), "--squash", "--delete-branch"]
    if repo:
        merge_cmd += ["--repo", repo]
    try:
        merge_result = subprocess.run(merge_cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False

    if merge_result.returncode != 0:
        _log(f"{ticket_id}: auto-merge: gh pr merge failed (rc={merge_result.returncode}): {merge_result.stderr.strip()}")
        return False

    _log(f"{ticket_id}: auto-merge: PR #{pr_number} merged successfully")
    state["pr_merged"] = True
    state["daemon_archived"] = True
    _save_state_json(run_dir, state)
    return True


def handle_test_complete(
    ticket_id: str,
    run_dir: Path,
    repo: str | None,
    worktree_cwd: str | None = None,
) -> None:
    """Orchestrate PR lifecycle for a ticket at TEST_COMPLETE."""
    _log(f"{ticket_id}: TEST_COMPLETE PR lifecycle")
    if not _checkpoint_and_push_before_pr(ticket_id, cwd=worktree_cwd):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(ticket_id, run_dir, repo)
    if not auto_merge_pr(ticket_id, run_dir, repo):
        state_data = _load_state_json(run_dir)
        pr_number = state_data.get("pr_number")
        if pr_number:
            if not detect_pr_conflict(ticket_id, pr_number, run_dir, repo):
                _log(f"{ticket_id}: auto-merge failed but PR #{pr_number} has no conflicts — no state transition needed")
        else:
            _log(f"{ticket_id}: auto-merge failed but no pr_number in state.json — cannot check for conflicts")
        return
    check_and_close_issue(ticket_id, run_dir, repo)


_CONFLICT_SKIP_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
    "TEST_COMPLETE",
})


def detect_pr_conflict(
    ticket_id: str,
    pr_number: int,
    run_dir: Path,
    repo: str | None = None,
) -> bool:
    """Return True and write conflict metadata to state.json if the PR is CONFLICTING.

    Returns False on any error or when the PR is not conflicting (fail-safe).
    Does not perform any git operation.
    """
    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "mergeable"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        _log(f"{ticket_id}: conflict detection: gh not found")
        return False
    if result.returncode != 0:
        _log(f"{ticket_id}: conflict detection: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
        return False
    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        _log(f"{ticket_id}: conflict detection: invalid JSON from gh pr view")
        return False

    if pr_data.get("mergeable") != "CONFLICTING":
        return False

    # Fetch PR files to surface as potential conflict candidates
    files_cmd = ["gh", "pr", "view", str(pr_number), "--json", "files"]
    if repo:
        files_cmd += ["--repo", repo]
    conflicted_files: list[str] = []
    try:
        files_result = subprocess.run(files_cmd, capture_output=True, text=True, check=False)
        if files_result.returncode == 0:
            files_data = json.loads(files_result.stdout)
            conflicted_files = [f["path"] for f in files_data.get("files", []) if isinstance(f, dict) and "path" in f]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    state = _load_state_json(run_dir)
    pre_conflict_state = state.get("state", "")
    state["pre_conflict_state"] = pre_conflict_state
    state["conflict_detected_at"] = _now_iso()
    state["conflict_pr_number"] = pr_number
    state["conflicted_files"] = conflicted_files
    state["state"] = "CONFLICT_RESOLUTION_NEEDED"
    _save_state_json(run_dir, state)
    _log(f"{ticket_id}: PR #{pr_number} is CONFLICTING — transitioned to CONFLICT_RESOLUTION_NEEDED (was {pre_conflict_state!r}, {len(conflicted_files)} files)")
    return True


def scan_tickets(runs_dir: Path, worktrees_dir: Path | None = None) -> list[tuple[str, str]]:
    """Return (ticket_id, state) for all readable state.json files, sorted by ticket_id."""
    seen: dict[str, str] = {}

    # Scan worktrees first — they hold the most current state for active tickets
    if worktrees_dir and worktrees_dir.exists():
        for worktree_dir in sorted(worktrees_dir.iterdir()):
            ticket_id = worktree_dir.name
            if not re.match(r"^T\d{3,}$", ticket_id):
                continue
            state_path = worktree_dir / "runs" / ticket_id / "state.json"
            if not state_path.exists():
                continue
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
                if data.get("daemon_archived"):
                    _log(f"skipping {ticket_id}: daemon_archived=true")
                    continue
                state = data.get("state", "")
                if state:
                    seen[ticket_id] = state
            except (json.JSONDecodeError, OSError):
                _log(f"skipping {ticket_id}: corrupted state.json in worktree")

    # Also scan main repo runs/ for tickets without worktrees
    for state_path in sorted(runs_dir.glob("*/state.json")):
        ticket_id = state_path.parent.name
        if ticket_id in seen:
            continue  # worktree state takes priority
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            if data.get("daemon_archived"):
                _log(f"skipping {ticket_id}: daemon_archived=true")
                continue
            state = data.get("state", "")
            if state:
                seen[ticket_id] = state
        except (json.JSONDecodeError, OSError):
            _log(f"skipping {ticket_id}: corrupted or unreadable state.json")

    return list(seen.items())


def _get_run_dir(ticket_id: str, runs_dir: Path, worktrees_dir: Path | None = None) -> Path:
    """Return the run_dir holding the ticket's state — worktree takes priority."""
    if worktrees_dir:
        wt_run_dir = worktrees_dir / ticket_id / "runs" / ticket_id
        if wt_run_dir.exists():
            return wt_run_dir
    return runs_dir / ticket_id


def build_run_ticket_command(
    ticket_id: str,
    exec_cmd: str | None,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
) -> list[str]:
    """Build the run_ticket.py command list. exec_cmd is passed as a single string element."""
    cmd = [sys.executable, str(RUN_TICKET), ticket_id, "--auto"]
    if exec_cmd:
        cmd.extend(["--exec-cmd", exec_cmd])
    if auto_commit:
        cmd.append("--auto-commit")
    if auto_push:
        cmd.append("--auto-push")
    if auto_include_code:
        cmd.append("--auto-include-code")
    return cmd


def _clean_runtime_before_sync(ticket_id: str, cwd: str | None = None) -> tuple[list[str], list[str]]:
    """Aggressively clean *runtime garbage* before a sync/rebase.

    The rebase refuses to run as long as any tracked file is dirty or any
    untracked file would be overwritten. Runtime garbage (``runtime.log``,
    ``__pycache__/*.pyc``, daemon lock/pid, SQLite live DB, …) must never be
    the reason a sync fails. This helper:

    1. Parses ``git status --porcelain``.
    2. Splits dirty paths into runtime-ignored vs real-dirty.
    3. For each runtime-ignored path:
       - if it is tracked → ``git checkout HEAD -- path`` to discard the change;
       - if it is untracked (``??`` in porcelain) → ``rm -f`` from disk so the
         rebase has no untracked files to worry about;
       - ``__pycache__`` directories are removed recursively.

    Real-dirty paths are left untouched: they remain visible to the caller
    (and to git) so the regular clean-gate or auto-commit logic gets to
    decide what to do. The rebase will simply refuse if they are still
    around, which is the intended behaviour.

    Returns ``(cleaned, real_dirty)`` for logging/auditing.
    """
    # ``-uall`` expands untracked *directories* into their individual files so
    # we don't see ``?? runs/`` and treat it as a single mysterious path —
    # we need each ``.pyc`` / ``runtime.log`` to be classifiable.
    status = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        capture_output=True, text=True, check=False,
        cwd=cwd,
    )
    cleaned: list[str] = []
    real_dirty: list[str] = []
    if status.returncode != 0 or not status.stdout.strip():
        return cleaned, real_dirty

    base = Path(cwd) if cwd else Path(".")
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        flags = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip()
        if not path:
            continue

        if not is_runtime_ignored_path(path):
            real_dirty.append(path)
            continue

        full = base / path
        is_untracked = flags == "??"
        if is_untracked:
            try:
                if full.is_dir():
                    import shutil
                    shutil.rmtree(full, ignore_errors=True)
                else:
                    full.unlink(missing_ok=True)
                cleaned.append(f"rm:{path}")
            except OSError:
                pass
        else:
            # Tracked but dirty (legacy commits before .gitignore): reset to HEAD
            reset = subprocess.run(
                ["git", "checkout", "HEAD", "--", path],
                capture_output=True, text=True, check=False, cwd=cwd,
            )
            if reset.returncode == 0:
                cleaned.append(f"reset:{path}")
            else:
                # Last-resort: physically remove the working-tree copy
                try:
                    full.unlink(missing_ok=True)
                    cleaned.append(f"rm-fallback:{path}")
                except OSError:
                    pass

    if cleaned:
        _log(f"{ticket_id}: pre-sync hygiene cleaned {len(cleaned)} runtime path(s): {cleaned[:10]}")
    if real_dirty:
        _log(f"{ticket_id}: pre-sync hygiene preserved {len(real_dirty)} real dirty path(s): {real_dirty[:10]}")
    return cleaned, real_dirty


def _auto_commit_useful_dirty(
    ticket_id: str,
    real_dirty: list[str],
    cwd: str | None,
    push: bool,
) -> bool:
    """Auto-commit a non-empty ``real_dirty`` set via ``checkpoint_transition``.

    Used as a fallback right before ``git pull --rebase``: if the worker
    left real implementation files unstaged (T122: coder did not commit),
    we cannot rebase, so we commit them here on its behalf rather than
    refusing the cycle. Returns True on success, False otherwise.
    """
    message_lines = [
        f"chore({ticket_id}): pre-sync auto-commit",
        "",
        "Auto-committed by the daemon before `git pull --rebase` because the",
        "previous worker left useful implementation changes unstaged.",
        "",
        "Files:",
    ]
    for p in real_dirty[:20]:
        message_lines.append(f"- {p}")
    if len(real_dirty) > 20:
        message_lines.append(f"- … and {len(real_dirty) - 20} more")
    message_lines += ["", f"refs {ticket_id}"]
    message = "\n".join(message_lines)
    try:
        checkpoint_transition(
            ticket_id,
            message,
            push=push,
            include_code=True,
            cwd=cwd,
        )
        _log(
            f"{ticket_id}: pre-sync auto-commit ok "
            f"({len(real_dirty)} useful file(s), push={push})"
        )
        return True
    except CheckpointError as exc:
        _log(f"{ticket_id}: pre-sync auto-commit failed — {exc}")
        return False
    except DirtyTreeError as exc:
        _log(f"{ticket_id}: pre-sync auto-commit left dirty tree — {exc}")
        return False


def _sync_ticket_branch(
    ticket_id: str,
    branch: str,
    cwd: str | None = None,
    auto_commit: bool = False,
    auto_push: bool = False,
) -> bool:
    """Pull latest commits from remote with fast-forward only.

    Before pulling, runtime garbage is discarded and any remaining *useful*
    dirty paths are handled depending on configuration:

    - ``auto_commit=True``  → auto-commit the useful dirty (via
      ``checkpoint_transition(include_code=True)``) and, if ``auto_push``
      is set, push the resulting commit. This is the path that fixes T122:
      the coder finished but did not stage its own changes, so we commit
      them here rather than failing the rebase.
    - ``auto_commit=False`` → log a clear error and refuse to rebase.
      The caller skips the ticket without touching the user's changes.

    Returns True if in sync or remote branch not yet published.
    Returns False if diverged, rebase failed, or we refused to proceed.
    """
    cleaned, real_dirty = _clean_runtime_before_sync(ticket_id, cwd=cwd)

    if real_dirty:
        if auto_commit:
            _log(
                f"{ticket_id}: pre-sync useful dirty detected, "
                f"auto-committing before rebase: {real_dirty[:10]}"
            )
            if not _auto_commit_useful_dirty(
                ticket_id, real_dirty, cwd=cwd, push=auto_push
            ):
                _log(f"{ticket_id}: pre-sync auto-commit failed — sync skipped")
                return False
        else:
            _log(
                f"{ticket_id}: pre-sync refused — useful files dirty and "
                f"--auto-commit is disabled: {real_dirty[:10]}"
            )
            return False

    result = subprocess.run(
        ["git", "pull", "--rebase", "origin", branch],
        capture_output=True, text=True, check=False,
        cwd=cwd,
    )
    if result.returncode == 0:
        _log(f"{ticket_id}: sync branch {branch!r} ok")
        return True
    stderr = result.stderr.strip()
    if "couldn't find remote ref" in stderr or "no tracking information" in stderr:
        _log(f"{ticket_id}: sync branch {branch!r} — remote branch not found yet, skipping pull")
        return True
    _log(f"{ticket_id}: sync branch {branch!r} failed — rebase conflict: {stderr}")
    subprocess.run(["git", "rebase", "--abort"], cwd=cwd, capture_output=True)
    return False


def _get_current_branch() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _spawn_worker_process(cmd: list[str], *, cwd: str, env: dict[str, str]) -> subprocess.Popen:
    """Start ``run_ticket.py`` in the background. Separated for testability."""
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_ticket(
    ticket_id: str,
    exec_cmd: str,
    dry_run: bool,
    runs_dir: Path,
    worktrees_dir: Path | None = None,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
    state_dir: Path | None = None,
) -> None:
    """Launch run_ticket.py --auto for one ticket in the background.

    Returns immediately after spawning the worker so the daemon can keep
    polling GitHub and running the intelligence/readiness pipeline in parallel.
    Call ``reap_completed_workers`` each cycle to collect exit codes and apply
    retry policy.
    """
    if dry_run:
        _log(f"dry-run: would launch {ticket_id} --auto --exec-cmd {exec_cmd!r}")
        return

    _state_dir = state_dir if state_dir is not None else runs_dir

    # Determine if this ticket has a dedicated worktree
    worktree_path: Path | None = None
    if worktrees_dir:
        wt = get_ticket_worktree_path(ticket_id, worktrees_dir)
        if wt.exists():
            worktree_path = wt
        else:
            # Try on-demand creation before falling back
            ticket_state = _load_state_json(runs_dir / ticket_id)
            branch = ticket_state.get("branch")
            if branch:
                ok, msg = create_ticket_worktree(ticket_id, branch, worktrees_dir, repo_root=REPO_ROOT)
                _log(f"{ticket_id}: on-demand worktree: {msg}")
                if ok:
                    worktree_path = wt
            if worktree_path is None or not worktree_path.exists():
                _log(f"skipping {ticket_id}: worktrees_dir set but worktree unavailable — no legacy fallback")
                return

    if worktree_path is not None:
        run_dir = worktree_path / "runs" / ticket_id
        cwd = str(worktree_path)
    else:
        run_dir = runs_dir / ticket_id
        cwd = None

    run_dir.mkdir(parents=True, exist_ok=True)

    if not _acquire_lock(run_dir):
        _log(f"skipping {ticket_id}: already running (lock held)")
        return

    lock_released = False
    try:
        if worktree_path is not None:
            ticket_state = _load_state_json(run_dir)
            branch = ticket_state.get("branch")

            if branch and not _sync_ticket_branch(
                ticket_id,
                branch,
                cwd=cwd,
                auto_commit=auto_commit,
                auto_push=auto_push,
            ):
                _log(f"skipping {ticket_id}: branch sync failed in worktree")
                return
        else:
            ticket_state = _load_state_json(run_dir)
            expected_branch = ticket_state.get("branch")
            branch = expected_branch
            if expected_branch:
                current_branch = _get_current_branch()
                if current_branch != expected_branch:
                    _log(
                        f"skipping {ticket_id}: branch mismatch "
                        f"current={current_branch!r} expected={expected_branch!r}"
                    )
                    return
                if not _sync_ticket_branch(
                    ticket_id,
                    expected_branch,
                    auto_commit=auto_commit,
                    auto_push=auto_push,
                ):
                    _log(f"skipping {ticket_id}: branch sync failed — diverged from remote")
                    return

            if not _ensure_clean_working_tree(ticket_id, auto_push=auto_push):
                return

        cmd = build_run_ticket_command(ticket_id, exec_cmd, auto_commit, auto_push, auto_include_code)
        launch_cwd = cwd if cwd is not None else os.getcwd()
        if worktree_path is not None:
            _log(f"launching worker {ticket_id} in worktree={worktree_path}: {shlex.join(cmd)}")
        else:
            _log(f"Running ticket command: {shlex.join(cmd)}")

        proc = _spawn_worker_process(cmd, cwd=launch_cwd, env=_no_bytecode_env())
        _set_lock_holder_pid(run_dir, proc.pid)
        worktree_label = str(worktree_path) if worktree_path is not None else ""
        _register_worker(_state_dir, ticket_id, branch, worktree_label, pid=proc.pid)
        _ACTIVE_WORKERS[ticket_id] = {
            "proc": proc,
            "run_dir": run_dir,
        }
        _log(f"{ticket_id}: worker started pid={proc.pid} (background)")
        lock_released = True
    finally:
        if not lock_released:
            _release_lock(run_dir)


# ── issue polling ─────────────────────────────────────────────────────────────

def load_issue_index(state_dir: Path) -> dict[str, str]:
    """Load the anti-duplicate index mapping issue numbers to ticket IDs.

    Reads from the local JSON file (gitignored, written by save_issue_index).
    The JSON file is the daemon's working copy; SQLite is written in parallel
    for the board/dashboard to consume.
    """
    path = state_dir / ISSUE_INDEX_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_issue_index(state_dir: Path, index: dict[str, str]) -> None:
    """Persist the anti-duplicate index.

    Writes to both the local JSON file (daemon working copy) and SQLite
    (for board/dashboard). The JSON file is gitignored — see .gitignore.
    """
    path = state_dir / ISSUE_INDEX_FILENAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=2), encoding="utf-8")
    tmp.replace(path)

    db_path = _ensure_db()
    if db_path:
        try:
            for num_str, tid in index.items():
                _rdb_record_intake(db_path, int(num_str), tid)
        except Exception as exc:
            _log(f"SQLite issue index sync failed: {exc}")


def next_ticket_id(runs_dir: Path, reserved: set[str] | None = None) -> str:
    """Compute the next available ticket ID by scanning runs/T*/ and the optional reserved set."""
    max_num = 0
    for p in runs_dir.glob("T*/"):
        m = re.match(r"T(\d+)$", p.name)
        if m:
            max_num = max(max_num, int(m.group(1)))
    for tid in (reserved or ()):
        m = re.match(r"T(\d+)$", tid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"T{max_num + 1:03d}"


def ticket_sort_key(ticket_id: str) -> int:
    """Sort ticket IDs numerically so T104 runs before T105/T106/T107."""
    match = re.match(r"T(\d+)$", ticket_id)
    if not match:
        return 999999
    return int(match.group(1))


def extract_ticket_id_from_title(title: str) -> str | None:
    """Return explicit TXXX from an issue title, if present."""
    match = re.search(r"\bT\d{3,}\b", title or "", re.IGNORECASE)
    if not match:
        return None
    return match.group(0).upper()


def issue_intake_sort_key(issue: dict) -> tuple[int, int]:
    """Order intake candidates by ticket id from the title, then GitHub issue number.

    GitHub issue numbers reflect creation order, not ticket sequence — issue #5
    may be T002 while issue #24 is T001. Sorting by extracted ticket id ensures
    T001 is ingested before T002 even when its GitHub number is higher.
    """
    title = issue.get("title", "")
    ticket_id = extract_ticket_id_from_title(title)
    ticket_ord = ticket_sort_key(ticket_id) if ticket_id else 999_999
    return (ticket_ord, int(issue.get("number") or 0))


def slugify_title(title: str) -> str:
    """Convert an issue title to a URL-safe branch slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:50].rstrip("-")
    return slug or "issue"


def _try_reconcile_existing_worktree(
    ticket_id: str,
    issue_number: str,
    worktrees_dir: Path,
    index: dict[str, str],
    state_dir: Path,
) -> bool:
    """Adopt a pre-existing worktree into the intake index when ``state.json`` is present."""
    worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
    if not worktree_path.is_dir():
        return False

    run_dir = worktree_path / "runs" / ticket_id
    state_path = run_dir / "state.json"
    if not state_path.is_file():
        _log(
            f"{ticket_id}: worktree exists at {worktree_path} but no {state_path.name} "
            f"— cannot reconcile issue #{issue_number}"
        )
        return False

    if index.get(issue_number) == ticket_id:
        return True

    index[issue_number] = ticket_id
    save_issue_index(state_dir, index)
    _log(f"{ticket_id}: reconciled existing worktree for issue #{issue_number}")

    db_path = _ensure_db()
    if db_path:
        try:
            ticket_state = _load_state_json(run_dir)
            _rdb_upsert_ticket(
                db_path,
                ticket_id,
                issue_number=int(issue_number),
                branch=ticket_state.get("branch"),
                state=ticket_state.get("state", "INIT"),
                run_dir=str(run_dir),
                worktree_path=str(worktree_path),
            )
        except Exception as exc:
            _log(f"SQLite ticket upsert failed for reconciled {ticket_id}: {exc}")
    return True


def clear_stale_run_dir(worktree_path: Path, ticket_id: str) -> bool:
    """Remove a pre-existing ``runs/<ticket_id>/`` tree left on ``origin/main``.

    Merged tickets commit their run artifacts to main. Re-ingesting the same
    ticket id on a fresh branch would otherwise fail ``check_state_absent``.
    Returns True when a stale directory was removed.
    """
    stale = worktree_path / "runs" / ticket_id
    if not stale.is_dir():
        return False
    shutil.rmtree(stale)
    return True


def fetch_ready_issues(label: str, repo: str | None) -> list[dict]:
    """Call `gh issue list` and return open issues with the given label. Returns [] on any failure."""
    cmd = ["gh", "issue", "list", "--label", label, "--json", "number,title", "--state", "open"]
    if repo:
        cmd += ["--repo", repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"gh issue list failed (rc={result.returncode}) — skipping issue polling")
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except FileNotFoundError:
        _log("gh not found — skipping issue polling")
        return []
    except json.JSONDecodeError:
        _log("gh returned invalid JSON — skipping issue polling")
        return []


def call_issue_intake(issue_number: int, ticket_id: str, branch_slug: str, repo: str | None, push: bool = False, cwd: str | None = None) -> bool:
    """Run run_issue_intake.py for one issue. Returns True on success."""
    cmd = [
        sys.executable, str(RUN_ISSUE_INTAKE),
        "--issue", str(issue_number),
        "--ticket-id", ticket_id,
        "--branch-slug", branch_slug,
    ]
    if repo:
        cmd += ["--repo", repo]
    if push:
        cmd.append("--push")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=_no_bytecode_env(),
    )
    for line in result.stdout.splitlines():
        _log(f"intake {ticket_id}: {line}")
    for line in result.stderr.splitlines():
        _log(f"intake {ticket_id} [err]: {line}")
    return result.returncode == 0


def poll_github_issues(
    runs_dir: Path,
    label: str,
    repo: str | None,
    worktrees_dir: Path | None = None,
    state_dir: Path | None = None,
) -> None:
    """Detect ready GitHub issues and create local runs for new ones."""
    _state_dir = state_dir if state_dir is not None else runs_dir

    issues = fetch_ready_issues(label, repo)
    if not issues:
        _log(f"no issues found with label={label!r}")
        return

    index = load_issue_index(_state_dir)
    candidates = sorted(
        [i for i in issues if str(i["number"]) not in index],
        key=issue_intake_sort_key,
    )
    already_ingested = [i for i in issues if str(i["number"]) in index]
    for issue in already_ingested:
        _log(f"issue #{issue['number']} already ingested as {index[str(issue['number'])]} — skipping")

    if not candidates:
        _log(f"found {len(issues)} issue(s) with label={label!r} — all already ingested")
        return

    _log(f"found {len(candidates)} candidate issue(s)")

    for issue in candidates:
        number = str(issue["number"])
        title = issue.get("title", "")
        ticket_id = extract_ticket_id_from_title(title)
        if ticket_id is None:
            ticket_id = next_ticket_id(runs_dir, reserved=set(index.values()))
        elif ticket_id in index.values():
            continue
        elif worktrees_dir and ticket_id and _try_reconcile_existing_worktree(
            ticket_id, number, worktrees_dir, index, _state_dir,
        ):
            break  # one intake/reconcile action per daemon cycle
        elif (runs_dir / ticket_id).exists():
            _log(f"issue #{number}: ticket {ticket_id} already exists — skipping intake")
            continue

        slug = slugify_title(title)
        branch = f"ticket/{ticket_id}-{slug}"
        _log(f"ingesting issue #{number} ({title!r}) as {ticket_id} slug={slug!r}")

        if not worktrees_dir:
            _log(
                f"issue #{number}: worktrees_dir not configured — ephemeral intake requires"
                " --worktrees-dir; skipping (no legacy fallback)"
            )
            continue

        _log(f"{ticket_id}: ephemeral intake — fetching origin/main")
        fetched, fetch_msg = fetch_origin_main(repo_root=REPO_ROOT)
        if not fetched:
            _log(f"{ticket_id}: {fetch_msg} — skipping issue #{number}")
            continue
        _log(f"{ticket_id}: {fetch_msg}")

        _log(f"{ticket_id}: creating branch {branch} and worktree directly")
        created, create_msg = create_ticket_branch_and_worktree(
            ticket_id, branch, worktrees_dir, repo_root=REPO_ROOT,
        )
        if not created:
            if worktrees_dir and _try_reconcile_existing_worktree(
                ticket_id, number, worktrees_dir, index, _state_dir,
            ):
                break
            _log(f"{ticket_id}: {create_msg} — skipping issue #{number}")
            continue
        _log(f"{ticket_id}: {create_msg}")

        worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
        if clear_stale_run_dir(worktree_path, ticket_id):
            _log(f"{ticket_id}: removed stale runs/{ticket_id}/ from main checkout")
        intake_ok = call_issue_intake(
            int(number), ticket_id, slug, repo, push=True, cwd=str(worktree_path),
        )
        if not intake_ok:
            _log(f"{ticket_id}: intake failed — rolling back branch+worktree")
            for msg in cleanup_failed_intake(
                ticket_id, branch, worktrees_dir, repo_root=REPO_ROOT,
            ):
                _log(f"{ticket_id}: cleanup: {msg}")
            _log(f"intake failed for issue #{number} — will retry next cycle")
            continue

        index[number] = ticket_id
        save_issue_index(_state_dir, index)
        _log(f"issue #{number} ingested as {ticket_id}")
        db_path = _ensure_db()
        if db_path:
            try:
                _rdb_upsert_ticket(
                    db_path, ticket_id,
                    issue_number=int(number),
                    branch=branch,
                    state="INIT",
                )
            except Exception as exc:
                _log(f"SQLite ticket upsert failed for {ticket_id}: {exc}")
            try:
                _attach_ticket_to_collecting_batch(db_path, ticket_id)
            except Exception as exc:
                _log(f"backlog batch attach failed for {ticket_id}: {exc}")
        break  # one successful intake per daemon cycle


def _resolve_backlog_setting(db_path, key: str, fallback):
    """Look up a backlog setting via the registry, returning ``fallback`` on error."""
    try:
        value = _runtime_settings.get_setting(db_path, key)
    except Exception:
        return fallback
    return value if value is not None else fallback


def _attach_ticket_to_collecting_batch(db_path, ticket_id: str) -> None:
    """Place a newly intaken ticket into the current collecting batch.

    Respects ``BACKLOG_ALLOW_PARALLEL_BATCHES``: when False and another batch
    is already ``dispatching``, the new batch (or the open collecting one) is
    held with ``freeze_blocked=TRUE`` so the dispatcher's graph stays stable.
    """
    allow_parallel = bool(_resolve_backlog_setting(
        db_path, "BACKLOG_ALLOW_PARALLEL_BATCHES", False,
    ))
    max_size = int(_resolve_backlog_setting(
        db_path, "BACKLOG_MAX_BATCH_SIZE", 50,
    ))
    batch_id = _backlog_batch.get_or_create_collecting_batch(
        db_path,
        allow_parallel_batches=allow_parallel,
        max_batch_size=max_size,
    )
    inserted = _backlog_batch.add_ticket_to_batch(db_path, batch_id, ticket_id)
    if inserted:
        _log(f"backlog: ticket {ticket_id} attached to batch {batch_id}")


def process_backlog_batches(
    db_path,
    runs_dir: Path,
    *,
    exec_cmd: str,
    now: str | None = None,
) -> None:
    """Drive the batch lifecycle once per daemon cycle.

    1. Freeze idle (or size-capped) collecting batches.
    2. Run the global dependency analyzer for ``frozen`` and retryable
       ``dependency_analysis_failed`` batches.
    3. Transition ``readiness_running`` batches to ``dispatching`` once every
       member has a completed readiness row.
    4. Transition ``dispatching`` batches to ``completed`` once every member
       has reached a terminal runtime state; unblock waiting collecting
       batches.

    Pure orchestration: per-step persistence lives in ``backlog_batch`` and
    ``global_dependency_analyzer``.
    """
    if db_path is None:
        return

    idle_minutes = int(_resolve_backlog_setting(
        db_path, "BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES", 10,
    ))
    max_size = int(_resolve_backlog_setting(
        db_path, "BACKLOG_MAX_BATCH_SIZE", 50,
    ))
    max_attempts = int(_resolve_backlog_setting(
        db_path, "BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS", 3,
    ))
    cooldown_minutes = int(_resolve_backlog_setting(
        db_path, "BACKLOG_DEPENDENCY_ANALYSIS_RETRY_COOLDOWN_MINUTES", 5,
    ))

    try:
        frozen_ids = _backlog_batch.try_freeze_idle_batches(
            db_path,
            idle_timeout_minutes=idle_minutes,
            max_batch_size=max_size,
            now=now,
        )
    except Exception as exc:
        _log(f"backlog: try_freeze_idle_batches failed: {exc}")
        frozen_ids = []
    for batch_id in frozen_ids:
        _log(f"backlog: batch {batch_id} frozen")

    try:
        ready_batches = _backlog_batch.pick_batches_ready_for_dependency_analysis(
            db_path, now=now, max_attempts=max_attempts,
        )
    except Exception as exc:
        _log(f"backlog: pick_batches_ready_for_dependency_analysis failed: {exc}")
        ready_batches = []

    for batch_id in ready_batches:
        try:
            _backlog_batch.mark_dependency_analysis_attempt_started(
                db_path, batch_id, now=now,
            )
        except _backlog_batch.BatchTransitionError as exc:
            _log(f"backlog: batch {batch_id} cannot start analysis: {exc}")
            continue
        outcome = _global_dependency_analyzer.run_global_analysis(
            db_path, runs_dir, batch_id, exec_cmd=exec_cmd,
        )
        if outcome.success:
            try:
                _backlog_batch.mark_dependency_analysis_succeeded(db_path, batch_id)
                _log(
                    f"backlog: batch {batch_id} analysis ok "
                    f"({outcome.persisted_ticket_count} ticket(s))"
                )
            except _backlog_batch.BatchTransitionError as exc:
                _log(f"backlog: batch {batch_id} success transition failed: {exc}")
        else:
            try:
                result = _backlog_batch.mark_dependency_analysis_failed(
                    db_path, batch_id,
                    error=outcome.error or "unknown",
                    cooldown_minutes=cooldown_minutes,
                    max_attempts=max_attempts,
                    now=now,
                )
                _log(
                    f"backlog: batch {batch_id} analysis failed "
                    f"attempt={result['attempts']} exhausted={result['exhausted']}"
                )
            except Exception as exc:
                _log(f"backlog: batch {batch_id} failure persist failed: {exc}")

    _advance_readiness_running_batches(db_path)
    _advance_dispatching_batches(db_path)


def _advance_readiness_running_batches(db_path) -> None:
    try:
        batches = _rdb_list_backlog_batches(
            db_path, status=_backlog_batch.BatchStatus.READINESS_RUNNING.value,
        )
    except Exception as exc:
        _log(f"backlog: list readiness_running failed: {exc}")
        return
    for batch in batches:
        batch_id = batch["batch_id"]
        members = _backlog_batch.list_batch_tickets(db_path, batch_id)
        if not members:
            continue
        all_done = True
        for ticket_id in members:
            try:
                ready = _rdb_get_ticket_readiness(db_path, ticket_id)
            except Exception:
                ready = None
            status = (ready or {}).get("readiness_status") or ""
            if status in {"", "not_started", "queued", "running"}:
                all_done = False
                break
        if all_done:
            try:
                _backlog_batch.transition_batch(
                    db_path, batch_id,
                    _backlog_batch.BatchStatus.READINESS_RUNNING.value,
                    _backlog_batch.BatchStatus.DISPATCHING.value,
                )
                _log(f"backlog: batch {batch_id} dispatching")
            except _backlog_batch.BatchTransitionError as exc:
                _log(f"backlog: batch {batch_id} dispatch transition failed: {exc}")


_TERMINAL_TICKET_STATES = frozenset({"TEST_COMPLETE", "CANCELLED"})


def _advance_dispatching_batches(db_path) -> None:
    try:
        batches = _rdb_list_backlog_batches(
            db_path, status=_backlog_batch.BatchStatus.DISPATCHING.value,
        )
    except Exception as exc:
        _log(f"backlog: list dispatching failed: {exc}")
        return
    completed_any = False
    for batch in batches:
        batch_id = batch["batch_id"]
        members = _backlog_batch.list_batch_tickets(db_path, batch_id)
        if not members:
            continue
        all_terminal = True
        for ticket_id in members:
            try:
                row = _rdb_get_ticket_runtime(db_path, ticket_id)
            except Exception:
                row = None
            state = ((row or {}).get("state") or "").upper()
            archived = bool((row or {}).get("daemon_archived"))
            if not (state in _TERMINAL_TICKET_STATES or archived):
                all_terminal = False
                break
        if all_terminal:
            try:
                _backlog_batch.transition_batch(
                    db_path, batch_id,
                    _backlog_batch.BatchStatus.DISPATCHING.value,
                    _backlog_batch.BatchStatus.COMPLETED.value,
                    extra_fields={"completed_at": _now_iso()},
                )
                _log(f"backlog: batch {batch_id} completed")
                completed_any = True
            except _backlog_batch.BatchTransitionError as exc:
                _log(f"backlog: batch {batch_id} complete transition failed: {exc}")
    if completed_any:
        try:
            _backlog_batch.unblock_freezing_for_pending_collecting_batches(db_path)
        except Exception as exc:
            _log(f"backlog: unblock pending batches failed: {exc}")


def poll_ticket_pipeline(
    db_path: "Path | None",
    runs_dir: Path,
    worktrees_dir: Path | None,
    project_root: Path,
    exec_cmd: str,
    *,
    project_id: str | None = None,
) -> None:
    """Run intelligence/readiness for tickets that still need pipeline work.

    Processes up to ``_PIPELINE_TICKETS_PER_CYCLE`` tickets per daemon cycle so
    orchestration keeps moving while coding workers run in the background.
    """
    if db_path is None or not _is_auto_pipeline_enabled(db_path):
        return

    tickets = sorted(scan_tickets(runs_dir, worktrees_dir), key=lambda t: ticket_sort_key(t[0]))
    ticket_ids = [ticket_id for ticket_id, _state in tickets]

    for _ in range(_PIPELINE_TICKETS_PER_CYCLE):
        next_id = _find_next_pipeline_ticket(db_path, ticket_ids)
        if next_id is None:
            return

        _log(f"pipeline: processing {next_id}")
        try:
            ran = _process_ticket_pipeline(
                db_path,
                next_id,
                project_root,
                exec_cmd,
                worktrees_dir=worktrees_dir,
                project_id=project_id,
            )
        except Exception as exc:
            _log(f"pipeline: failed for {next_id}: {exc}")
            return
        if ran:
            _log(f"pipeline: finished {next_id}")


def poll_project_map(runs_dir: Path, repo: str | None, worktrees_dir: Path | None = None) -> None:
    """Run run_issue_mapper.py to refresh the project dependency map."""
    cmd = [sys.executable, str(RUN_ISSUE_MAPPER), "--runs-dir", str(runs_dir)]
    if repo:
        cmd += ["--repo", repo]
    if worktrees_dir:
        cmd += ["--worktrees-dir", str(worktrees_dir)]
    _log("running issue mapper")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        for line in result.stdout.splitlines():
            _log(f"mapper: {line}")
        if result.returncode != 0:
            for line in result.stderr.splitlines():
                _log(f"mapper [err]: {line}")
            _log(f"mapper exited rc={result.returncode}")
    except FileNotFoundError:
        _log("mapper: run_issue_mapper.py not found")


def _load_project_map(runs_dir: Path, worktrees_dir: "Path | None" = None) -> "dict | None":
    path = runs_dir / PROJECT_MAP_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _dispatcher_enabled(db_path: "Path | None") -> tuple[bool, str]:
    """Return ``(enabled, mode)`` for the current dispatcher configuration.

    Tolerates a missing DB by returning ``(False, "off")`` so callers can keep
    using the legacy scheduling path without raising.
    """
    if db_path is None:
        return False, "off"
    try:
        mode = _get_dispatcher_mode(db_path)
    except Exception as exc:
        _log(f"dispatcher mode resolution failed — defaulting to off: {exc}")
        return False, "off"
    return mode != "off", mode


def _launch_blocked_by_eligibility(
    db_path: "Path | None",
    project_root: Path,
    ticket_id: str,
    run_dir: Path,
    project_id: str | None,
) -> str | None:
    """Return a human-readable block reason when the ticket must not spawn a worker."""
    if db_path is None:
        return None
    ticket_path = run_dir / "ticket.md"
    if not ticket_path.is_file():
        return None
    try:
        content = ticket_path.read_text(encoding="utf-8")
        result = _evaluate_eligibility(
            db_path,
            project_root,
            ticket_id,
            ticket_content=content,
            project_id=project_id,
        )
    except Exception as exc:
        return f"eligibility check failed: {exc}"
    if result.get("ready_to_take"):
        return None
    return result.get("reason") or result.get("status") or "not ready to take"


def _select_tickets_via_dispatcher(
    db_path: "Path | None",
    project_root: Path,
    runs_dir: Path,
    worktrees_dir: Path | None,
    mode: str,
    *,
    project_id: str | None = None,
) -> list[tuple[str, str]]:
    """Return ``[(ticket_id, state), ...]`` ranked by the dispatcher.

    Filters to states in ``AUTO_RUNNABLE_STATES`` so the caller's loop can run
    the existing retry/cooldown/worker-registry logic untouched. Returns ``[]``
    on any failure or when the dispatcher reports ``not_implemented`` — the
    caller must not fall back to legacy scheduling while dispatcher is enabled.
    """
    if db_path is None:
        return []
    try:
        payload = _get_recommended_tickets(
            db_path, project_root, mode=mode, project_id=project_id, worktrees_dir=worktrees_dir,
        )
    except Exception as exc:
        _log(f"dispatcher get_recommended_tickets failed: {exc}")
        return []
    if payload.get("not_implemented"):
        return []
    selected: list[tuple[str, str]] = []
    for rec in payload.get("recommendations", []):
        ticket_id = rec.get("ticket_id")
        if not ticket_id:
            continue
        run_dir = _get_run_dir(ticket_id, runs_dir, worktrees_dir)
        ticket_state = _load_state_json(run_dir).get("state", "")
        if ticket_state in AUTO_RUNNABLE_STATES:
            selected.append((ticket_id, ticket_state))
    return selected


def run_once(
    exec_cmd: str,
    dry_run: bool,
    runs_dir: Path,
    worktrees_dir: Path | None = None,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
    repo: str | None = None,
    max_workers: int = 1,
    use_project_map: bool = False,
    state_dir: Path | None = None,
    project_root: Path | None = None,
    project_id: str | None = None,
) -> None:
    """Scan all tickets and process auto-runnable ones."""
    _state_dir = state_dir if state_dir is not None else runs_dir
    reap_completed_workers(_state_dir)
    _db_path = _ensure_db()
    dispatcher_enabled, dispatcher_mode = _dispatcher_enabled(_db_path)

    all_tickets = sorted(scan_tickets(runs_dir, worktrees_dir), key=lambda t: ticket_sort_key(t[0]))

    if use_project_map:
        project_map = _load_project_map(runs_dir, worktrees_dir=worktrees_dir)
        if project_map:
            next_recommended = project_map.get("next_recommended")
            if next_recommended:
                # Move next_recommended to front of the list
                reordered = [t for t in all_tickets if t[0] == next_recommended]
                reordered += [t for t in all_tickets if t[0] != next_recommended]
                _log(f"project-map scheduling: next_recommended={next_recommended}")
                legacy_tickets = reordered
            else:
                _log("project-map: no next_recommended — falling back to FIFO")
                legacy_tickets = all_tickets
        else:
            _log("project-map: map absent — falling back to FIFO")
            legacy_tickets = all_tickets
    else:
        legacy_tickets = all_tickets

    if dispatcher_enabled:
        _log(f"scheduling: dispatcher (mode={dispatcher_mode})")
        _resolved_project_root = project_root if project_root is not None else REPO_ROOT
        _resolved_project_id = project_id or os.environ.get("PROJECT_NAME")
        dispatcher_tickets = _select_tickets_via_dispatcher(
            _db_path,
            _resolved_project_root,
            runs_dir,
            worktrees_dir,
            dispatcher_mode,
            project_id=_resolved_project_id,
        )
        if dispatcher_tickets:
            tickets = dispatcher_tickets
        else:
            _log("dispatcher returned no runnable tickets; launching nothing")
            return
    else:
        _log(f"scheduling: legacy (dispatcher=off)")
        tickets = legacy_tickets

    if not tickets:
        _log("no tickets found")
        return

    for ticket_id, state in tickets:
        run_dir = _get_run_dir(ticket_id, runs_dir, worktrees_dir)
        worktree_path = worktrees_dir / ticket_id if worktrees_dir else None
        worktree_cwd = str(worktree_path) if worktree_path and worktree_path.exists() else None

        if _db_path:
            try:
                ticket_data = _load_state_json(run_dir)
                upsert_fields: dict = {
                    "state": state,
                    "branch": ticket_data.get("branch"),
                    "issue_number": ticket_data.get("issue_number"),
                    "run_dir": str(run_dir),
                    "worktree_path": worktree_cwd,
                    "daemon_archived": int(bool(ticket_data.get("daemon_archived"))),
                    "pr_number": ticket_data.get("pr_number"),
                }
                pr_number = ticket_data.get("pr_number")
                if pr_number and not dry_run:
                    from ticket_merge_state import fetch_github_pr_state_label

                    gh_state = fetch_github_pr_state_label(
                        REPO_ROOT, int(pr_number), repo=repo
                    )
                    if gh_state:
                        upsert_fields["pr_state"] = gh_state
                _rdb_upsert_ticket(_db_path, ticket_id, **upsert_fields)
            except Exception as exc:
                _log(f"SQLite ticket sync failed for {ticket_id}: {exc}")

        # Conflict detection: check any ticket that has a PR and is not already
        # in a conflict or terminal state.
        if state not in _CONFLICT_SKIP_STATES:
            ticket_data_for_conflict = _load_state_json(run_dir)
            pr_number_for_conflict = ticket_data_for_conflict.get("pr_number")
            if pr_number_for_conflict and not dry_run:
                if detect_pr_conflict(ticket_id, pr_number_for_conflict, run_dir, repo):
                    # State was updated to CONFLICT_RESOLUTION_NEEDED — skip further processing
                    continue

        if state in AUTO_RUNNABLE_STATES:
            _log(f"detected {ticket_id} state={state}")
            active_count = _count_live_workers(_state_dir)
            if active_count >= max_workers:
                _log(f"skipping {ticket_id}: max_workers={max_workers} reached ({active_count} active)")
                continue
            retry_state = _load_retry_state(run_dir)
            if _is_blocked_by_retry(ticket_id, retry_state):
                continue
            _resolved_project_root = project_root if project_root is not None else REPO_ROOT
            _resolved_project_id = project_id or os.environ.get("PROJECT_NAME")
            block_reason = _launch_blocked_by_eligibility(
                _db_path,
                _resolved_project_root,
                ticket_id,
                run_dir,
                _resolved_project_id,
            )
            if block_reason:
                _log(f"skipping {ticket_id}: not ready to take — {block_reason}")
                continue
            launch_ticket(
                ticket_id, exec_cmd, dry_run, runs_dir,
                worktrees_dir=worktrees_dir,
                auto_commit=auto_commit, auto_push=auto_push, auto_include_code=auto_include_code,
                state_dir=_state_dir,
            )
        elif state == "TEST_COMPLETE":
            ticket_state = _load_state_json(run_dir)
            if ticket_state.get("issue_closed") or ticket_state.get("pr_skipped_no_diff"):
                _log(f"skipping {ticket_id}: TEST_COMPLETE already finalized")
                continue
            _log(f"detected {ticket_id} state=TEST_COMPLETE (human gate — PR lifecycle)")
            if not dry_run:
                handle_test_complete(ticket_id, run_dir, repo, worktree_cwd=worktree_cwd)
            else:
                _log(f"dry-run: would handle {ticket_id} TEST_COMPLETE PR lifecycle")
        elif state in HUMAN_GATE_STATES:
            if state == "PLAN_REVIEW_NEEDED":
                _log(f"detected {ticket_id} state=PLAN_REVIEW_NEEDED (human gate — checkpoint for visibility)")
                if not dry_run:
                    _checkpoint_and_push_before_pr(ticket_id, cwd=worktree_cwd)
                else:
                    _log(f"dry-run: would checkpoint/push {ticket_id} for PLAN_REVIEW_NEEDED")
            elif state == "CONFLICT_RESOLUTION_NEEDED":
                _log(f"Ticket {ticket_id} already in CONFLICT_RESOLUTION_NEEDED, skipping re-detection")
            _log(f"skipping {ticket_id} state={state} (human gate)")
        else:
            _log(f"skipping {ticket_id} state={state}")


def _check_runtime_clone() -> bool:
    """Return True if the daemon is running in a valid runtime clone.

    Accepts either:
    - REPO_ROOT contains .ai-dev-factory-runtime sentinel file, OR
    - AI_DEV_FACTORY_RUNTIME_ROOT env var is set (non-empty).

    Without one of these, the daemon refuses to start (exit code 2).
    This prevents accidental daemon launch in a human clone.
    """
    if (REPO_ROOT / ".ai-dev-factory-runtime").exists():
        return True
    if os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT"):
        return True
    print(
        "error: daemon must run in a runtime clone, not a human clone.\n"
        "  Create '.ai-dev-factory-runtime' at the repo root, or set AI_DEV_FACTORY_RUNTIME_ROOT.\n"
        "  See docs/ai/architecture.md for the expected runtime layout.",
        file=sys.stderr,
    )
    return False


def _resolve_repo_root(args: argparse.Namespace) -> Path:
    """Return the git project root this daemon serves.

    Managed-project daemons are spawned with ``cwd=<project_root>`` and
    ``AI_DEV_FACTORY_RUNTIME_ROOT=<project_runtime>``. Git operations (fetch,
    branch, worktree) must target the *managed* repo, not the factory clone that
  hosts ``run_daemon.py``.
    """
    if getattr(args, "project_root", None):
        root = Path(args.project_root).expanduser().resolve()
    elif os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT"):
        root = Path.cwd().resolve()
    else:
        return _SCRIPT_REPO_ROOT

    check = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if check.returncode != 0:
        print(
            f"error: project root is not a git repository: {root}\n"
            f"  {check.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    return Path(check.stdout.strip())


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local workflow daemon for ai-dev-factory")
    parser.add_argument("--exec-cmd", required=True, help="Command passed to run_ticket.py --auto")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without executing")
    parser.add_argument("--runs-dir", default="runs", help="Path to runs directory (default: runs)")
    parser.add_argument("--worktrees-dir", default=str(DEFAULT_WORKTREES_DIR), help=f"Base directory for per-ticket worktrees (default: {DEFAULT_WORKTREES_DIR})")
    parser.add_argument("--max-workers", type=int, default=1, help="Maximum concurrent ticket workers (default: 1)")
    parser.add_argument("--poll-issues", action="store_true", help="Enable GitHub issue polling")
    parser.add_argument("--issue-label", default="ai-ready", help="GitHub label to filter issues (default: ai-ready)")
    parser.add_argument("--issue-repo", default=None, help="GitHub repo (owner/repo) — defaults to current repo")
    parser.add_argument("--auto-commit", action="store_true", help="After each successful step, commit runs/ artifacts")
    parser.add_argument("--auto-push", action="store_true", help="After each successful auto-commit, push the ticket branch")
    parser.add_argument("--auto-include-code", action="store_true", help="With --auto-commit, also stage COMMIT_SCOPE paths (tools/, tests/, prompts/, tickets/, docs/, ai/)")
    parser.add_argument("--poll-project-map", action="store_true", help="Run issue mapper at each daemon cycle to refresh the project dependency map")
    parser.add_argument("--use-project-map", action="store_true", help="Use project map next_recommended for scheduling instead of FIFO (fallback to FIFO if map absent)")
    parser.add_argument("--project-root", default=None, help="Git root of the managed project (default: cwd when AI_DEV_FACTORY_RUNTIME_ROOT is set)")
    parser.add_argument("--project", default=None, help="Project id for runtime DB scoping (also sets PROJECT_NAME when unset)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if not _check_runtime_clone():
        return 2

    args = parse_args(argv)

    global REPO_ROOT
    REPO_ROOT = _resolve_repo_root(args)

    if args.project:
        os.environ.setdefault("PROJECT_NAME", args.project)

    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        rt = Path(runtime_root)
        runs_dir = rt / "runs"
        worktrees_dir = Path(args.worktrees_dir)
        global _LOG_FILE
        _LOG_FILE = rt / "logs" / "daemon.log"
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        state_dir = rt / "state"
    else:
        runs_dir = Path(args.runs_dir)
        worktrees_dir = Path(args.worktrees_dir)
        state_dir = _rr_resolve_state_dir(REPO_ROOT)

    if not runs_dir.exists():
        print(f"error: runs dir not found: {runs_dir}", file=sys.stderr)
        return 2

    # ── boot banner ──────────────────────────────────────────────────────
    # Print every piece of environment context up front so dashboard logs
    # let operators diagnose "daemon launched but degraded" issues without
    # extra digging.
    import shutil as _shutil  # local import to keep top-level imports clean
    gh_path = _shutil.which("gh") or "<missing>"
    git_path = _shutil.which("git") or "<missing>"
    try:
        repo_check = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        repo_top = repo_check.stdout.strip() if repo_check.returncode == 0 else "<not-a-git-repo>"
    except (OSError, subprocess.SubprocessError):
        repo_top = "<git-check-failed>"

    _log("=" * 60)
    _log("daemon boot — environment")
    _log(f"  repo_root      = {REPO_ROOT}")
    _log(f"  repo_toplevel  = {repo_top}")
    _log(f"  cwd            = {Path.cwd()}")
    _log(f"  runs_dir       = {runs_dir}")
    _log(f"  worktrees_dir  = {worktrees_dir}")
    _log(f"  state_dir      = {state_dir}")
    _log(f"  runtime_root   = {runtime_root or '<unset>'}")
    _log(f"  python         = {sys.executable}")
    _log(f"  git            = {git_path}")
    _log(f"  gh             = {gh_path}")
    _log(f"  exec_cmd       = {args.exec_cmd!r}")
    _log(f"  interval       = {args.interval}s  dry-run={args.dry_run}")
    _log(f"  max-workers    = {args.max_workers}")
    if args.project:
        _log(f"  project_id     = {args.project}")
    try:
        _boot_db = _ensure_db()
        _boot_mode = _get_dispatcher_mode(_boot_db) if _boot_db else "off"
    except Exception:
        _boot_mode = "off"
    _log(f"  dispatcher_mode = {_boot_mode}")
    try:
        _boot_pipeline = _is_auto_pipeline_enabled(_boot_db) if _boot_db else True
    except Exception:
        _boot_pipeline = True
    _log(f"  auto_pipeline  = {_boot_pipeline}")
    _log("=" * 60)

    # Strict refuse mode: if gh is missing while issue polling is requested,
    # fail fast rather than running a degraded loop.
    if args.poll_issues and gh_path == "<missing>":
        _log("FATAL: gh CLI not found in PATH — issue polling requested but cannot proceed.")
        _log("       Install gh or unset --poll-issues.")
        return 2
    if git_path == "<missing>":
        _log("FATAL: git not found in PATH — daemon cannot run.")
        return 2
    if repo_top.startswith("<"):
        _log(f"FATAL: REPO_ROOT is not a git working tree ({REPO_ROOT}).")
        _log("       Ensure the daemon launches from a git clone, not a stripped image.")
        return 2

    if not runtime_root:
        _log("WARNING: AI_DEV_FACTORY_RUNTIME_ROOT not set — using dev fallback paths")
    if args.poll_issues:
        _log(f"issue polling enabled label={args.issue_label!r} repo={args.issue_repo!r}")
    if args.auto_commit:
        _log(f"auto-commit enabled auto-push={args.auto_push} auto-include-code={args.auto_include_code}")
    if args.poll_project_map:
        _log("project-map polling enabled")
    if args.use_project_map:
        _log("project-map scheduling enabled (fallback: FIFO)")

    # Singleton guard — reject a second daemon instance before it can race on SQLite.
    if not _acquire_daemon_singleton(state_dir):
        _log("another daemon instance is already running (singleton lock held) — exiting cleanly")
        return 1

    _cleanup_stale_workers(state_dir)

    if args.once:
        reap_completed_workers(state_dir)
        if args.poll_issues:
            poll_github_issues(runs_dir, args.issue_label, args.issue_repo, worktrees_dir=worktrees_dir, state_dir=state_dir)
        poll_ticket_pipeline(
            _ensure_db(),
            runs_dir,
            worktrees_dir,
            REPO_ROOT,
            args.exec_cmd,
            project_id=args.project,
        )
        process_backlog_batches(
            _ensure_db(), runs_dir, exec_cmd=args.exec_cmd,
        )
        if args.poll_project_map:
            poll_project_map(runs_dir, args.issue_repo, worktrees_dir=worktrees_dir)
        run_once(
            args.exec_cmd, args.dry_run, runs_dir,
            worktrees_dir=worktrees_dir,
            auto_commit=args.auto_commit, auto_push=args.auto_push,
            auto_include_code=args.auto_include_code, repo=args.issue_repo,
            max_workers=args.max_workers,
            use_project_map=args.use_project_map,
            state_dir=state_dir,
            project_root=REPO_ROOT,
            project_id=args.project,
        )
        return 0

    try:
        while True:
            reap_completed_workers(state_dir)
            if args.poll_issues:
                poll_github_issues(runs_dir, args.issue_label, args.issue_repo, worktrees_dir=worktrees_dir, state_dir=state_dir)
            poll_ticket_pipeline(
                _ensure_db(),
                runs_dir,
                worktrees_dir,
                REPO_ROOT,
                args.exec_cmd,
                project_id=args.project,
            )
            process_backlog_batches(
                _ensure_db(), runs_dir, exec_cmd=args.exec_cmd,
            )
            if args.poll_project_map:
                poll_project_map(runs_dir, args.issue_repo, worktrees_dir=worktrees_dir)
            run_once(
                args.exec_cmd, args.dry_run, runs_dir,
                worktrees_dir=worktrees_dir,
                auto_commit=args.auto_commit, auto_push=args.auto_push,
                auto_include_code=args.auto_include_code, repo=args.issue_repo,
                max_workers=args.max_workers,
                use_project_map=args.use_project_map,
                state_dir=state_dir,
                project_root=REPO_ROOT,
                project_id=args.project,
            )
            _log(f"sleeping {args.interval}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        _log("interrupted — daemon stopping")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
