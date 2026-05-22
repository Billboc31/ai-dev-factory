"""Generic AI auto-fix loop orchestrator (T138).

Loop flow per iteration::

    collect_failure_context → call_ai_runtime → validate_patches
      → apply_patches → run_scripts_validation
        → success: session.status = "success"
        → failure / error: next iteration (counted toward max_retries)

Scripts are executed in-place from project_root (no git worktree) so that
patches applied to .ai-dev-factory/scripts/ are immediately visible.

Session persistence layout::

    {runtime_root}/auto-fix-sessions/{project_id}/{session_id}/state.json
    {runtime_root}/auto-fix-sessions/{project_id}/{session_id}/iter-{n}/run.log
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path

from auto_fix_proposer import (
    collect_failure_context,
    call_ai_runtime,
    validate_patches,
)

logger = logging.getLogger("supervisor")

_SCRIPTS_DIR = ".ai-dev-factory/scripts"
_DEFAULT_MAX_RETRIES = 3
_SCRIPT_TIMEOUT = int(os.environ.get("AI_DEV_FACTORY_SANDBOX_SCRIPT_TIMEOUT", "120"))


# ── Session management ────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_session(
    project_id: str,
    sandbox_id: str | None,
    max_retries: int,
    failing_step: str | None = None,
) -> dict:
    return {
        "session_id": uuid.uuid4().hex[:12],
        "project_id": project_id,
        "sandbox_id": sandbox_id,
        "max_retries": max_retries,
        "current_iteration": 0,
        "status": "running",
        "iterations": [],
        "failing_step": failing_step,
        "created_at": _now_utc(),
        "finished_at": None,
        "error": None,
    }


def _session_dir(project_id: str, session_id: str, runtime_root: Path) -> Path:
    return runtime_root / "auto-fix-sessions" / project_id / session_id


def persist_session(project_id: str, session: dict, runtime_root: Path) -> None:
    path = _session_dir(project_id, session["session_id"], runtime_root) / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")


def load_session(project_id: str, session_id: str, runtime_root: Path) -> dict | None:
    path = _session_dir(project_id, session_id, runtime_root) / "state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_sessions(project_id: str, runtime_root: Path) -> list[dict]:
    base = runtime_root / "auto-fix-sessions" / project_id
    if not base.exists():
        return []
    results = []
    for state_file in base.glob("*/state.json"):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sorted(results, key=lambda x: x.get("created_at", ""))


# ── Patch application ─────────────────────────────────────────────────────────

def apply_patches(patches: list[dict], project_root: Path) -> list[str]:
    """Write valid patches to disk. Returns list of changed relative paths."""
    changed = []
    for patch in patches:
        if not patch.get("valid", False):
            continue
        rel = patch["relative_path"]
        target = project_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch["content"], encoding="utf-8")
        if target.suffix == ".sh":
            target.chmod(target.stat().st_mode | 0o111)
        changed.append(rel)
    return changed


# ── In-place script validation ────────────────────────────────────────────────

def _append_iter_log(log_path: Path, text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text)


def run_scripts_validation(
    project_root: Path,
    iteration_dir: Path,
    script_timeout: int = _SCRIPT_TIMEOUT,
) -> tuple[bool, str | None, list[dict]]:
    """Run all *.sh scripts found in the scripts directory (sorted).

    Returns (success, error_message, steps).
    """
    log_path = iteration_dir / "run.log"
    steps: list[dict] = []

    scripts_dir = project_root / _SCRIPTS_DIR
    if not scripts_dir.exists():
        return True, None, steps

    for script_path in sorted(scripts_dir.glob("*.sh")):
        script_name = script_path.name
        step: dict = {
            "name": script_name, "status": "running",
            "started_at": _now_utc(), "exit_code": None,
        }
        steps.append(step)
        _append_iter_log(log_path, f"\n--- {script_name} ---\n")

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=script_timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            step["exit_code"] = result.returncode
            step["finished_at"] = _now_utc()
            step["status"] = "success" if result.returncode == 0 else "failed"
            if result.stdout:
                _append_iter_log(log_path, result.stdout)
            if result.stderr:
                _append_iter_log(log_path, result.stderr)
            if result.returncode != 0:
                return False, f"script failed (exit {result.returncode}): {script_name}", steps
        except subprocess.TimeoutExpired:
            step["status"] = "timeout"
            step["finished_at"] = _now_utc()
            return False, f"script timed out after {script_timeout}s: {script_name}", steps
        except OSError as exc:
            step["status"] = "error"
            step["finished_at"] = _now_utc()
            return False, f"script error {script_name}: {exc}", steps

    return True, None, steps


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_auto_fix_loop(
    session: dict,
    project_root: Path,
    exec_cmd: str,
    runtime_root: Path,
) -> None:
    """Run the auto-fix loop until success or max_retries.

    Mutates session in-place and persists after each iteration.
    """
    project_id = session["project_id"]
    sandbox_id = session["sandbox_id"]
    max_retries = session["max_retries"]
    failing_step = session.get("failing_step")

    for attempt in range(1, max_retries + 1):
        session["current_iteration"] = attempt
        persist_session(project_id, session, runtime_root)

        iteration: dict = {
            "iteration": attempt,
            "status": "running",
            "changed_files": [],
            "patches": [],
            "reasoning": None,
            "log_lines": [],
            "error": None,
            "started_at": _now_utc(),
            "finished_at": None,
            "steps": [],
        }
        session["iterations"].append(iteration)

        iter_dir = _session_dir(project_id, session["session_id"], runtime_root) / f"iter-{attempt}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        # 1. Collect context
        try:
            context = collect_failure_context(sandbox_id or "", project_root, runtime_root)
        except Exception as exc:
            _finish_iteration(iteration, "error", f"context collection failed: {exc}")
            persist_session(project_id, session, runtime_root)
            logger.warning("auto-fix loop: context collection failed iter=%d: %s", attempt, exc)
            continue

        # 2. Call AI runtime
        try:
            raw_patches = call_ai_runtime(context, exec_cmd, project_root, failing_step)
        except (ValueError, RuntimeError) as exc:
            _finish_iteration(iteration, "error", f"AI runtime error: {exc}")
            persist_session(project_id, session, runtime_root)
            logger.warning("auto-fix loop: AI runtime error iter=%d: %s", attempt, exc)
            continue

        # 3. Validate patches
        validated = validate_patches(raw_patches, project_root)
        iteration["patches"] = validated

        reasoning_parts = [p.get("reasoning", "") for p in raw_patches if p.get("reasoning")]
        if reasoning_parts:
            iteration["reasoning"] = " | ".join(reasoning_parts)

        valid_patches = [p for p in validated if p["valid"]]
        if not valid_patches:
            _finish_iteration(iteration, "error", "all proposed patches were out-of-scope (rejected)")
            persist_session(project_id, session, runtime_root)
            logger.warning("auto-fix loop: all patches invalid iter=%d", attempt)
            continue

        # 4. Apply valid patches
        try:
            changed = apply_patches(validated, project_root)
            iteration["changed_files"] = changed
        except OSError as exc:
            _finish_iteration(iteration, "error", f"patch application failed: {exc}")
            persist_session(project_id, session, runtime_root)
            logger.warning("auto-fix loop: patch apply failed iter=%d: %s", attempt, exc)
            continue

        # 5. Rerun validation
        success, error, steps = run_scripts_validation(project_root, iter_dir)
        iteration["steps"] = steps
        iteration["finished_at"] = _now_utc()

        log_path = iter_dir / "run.log"
        if log_path.exists():
            try:
                iteration["log_lines"] = log_path.read_text(encoding="utf-8").splitlines()[-200:]
            except OSError:
                pass

        if success:
            iteration["status"] = "success"
            session["status"] = "success"
            session["finished_at"] = _now_utc()
            session["current_iteration"] = attempt
            persist_session(project_id, session, runtime_root)
            logger.info("auto-fix loop: SUCCESS project_id=%s iter=%d", project_id, attempt)
            return

        # Update failing_step from the last failed script step
        last_failed = next((s for s in reversed(steps) if s["status"] == "failed"), None)
        if last_failed:
            failing_step = last_failed["name"]

        iteration["status"] = "failed"
        iteration["error"] = error
        persist_session(project_id, session, runtime_root)
        logger.info(
            "auto-fix loop: iteration %d failed project_id=%s error=%r",
            attempt, project_id, error,
        )

    # Max retries exhausted
    session["status"] = "failed"
    session["finished_at"] = _now_utc()
    persist_session(project_id, session, runtime_root)
    logger.info(
        "auto-fix loop: FAILED (max_retries=%d) project_id=%s",
        max_retries, project_id,
    )


def _finish_iteration(iteration: dict, status: str, error: str) -> None:
    iteration["status"] = status
    iteration["error"] = error
    iteration["finished_at"] = _now_utc()
