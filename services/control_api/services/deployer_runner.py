from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ..models.schemas import (
    ActionResult,
    DeployComponent,
    DeployHealthcheck,
    DeployLogsResponse,
    DeployProfile,
    DeployState,
)

if TYPE_CHECKING:
    from ..models.sandbox import SandboxState

logger = logging.getLogger("control-api")

_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()


def _get_lock(project_id: str) -> threading.Lock:
    with _locks_mutex:
        if project_id not in _locks:
            _locks[project_id] = threading.Lock()
        return _locks[project_id]


def _state_path(project_root: Path) -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        p = Path(runtime_root) / "state" / "deploy-state.json"
    else:
        p = project_root / ".ai-dev-factory" / "deploy-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _log_path(project_root: Path) -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        p = Path(runtime_root) / "logs" / "deploy.log"
    else:
        p = project_root / ".ai-dev-factory" / "deploy.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_deploy_profile(project_root: Path) -> DeployProfile | None:
    profile_path = project_root / ".ai-dev-factory" / "deploy.yml"
    if not profile_path.exists():
        return None
    try:
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        components = [
            DeployComponent(
                name=c["name"],
                type=c["type"],
                service=c.get("service"),
                command=c.get("command"),
            )
            for c in (data.get("components") or [])
        ]
        hc_data = data.get("healthcheck")
        healthcheck = None
        if isinstance(hc_data, dict):
            healthcheck = DeployHealthcheck(
                command=hc_data["command"],
                timeout=hc_data.get("timeout", 30),
                retries=hc_data.get("retries", 3),
                delay=hc_data.get("delay", 5),
            )

        def _parse_components(raw_list: list) -> list[DeployComponent]:
            return [
                DeployComponent(
                    name=c["name"],
                    type=c["type"],
                    service=c.get("service"),
                    command=c.get("command"),
                )
                for c in (raw_list or [])
            ]

        return DeployProfile(
            version=data["version"],
            project=data["project"],
            required_tools=data.get("required_tools") or [],
            components=components,
            healthcheck=healthcheck,
            undeploy=_parse_components(data.get("undeploy") or []),
            cleanup=_parse_components(data.get("cleanup") or []),
        )
    except Exception:
        logger.warning("deployer: failed to parse deploy.yml at %s", profile_path)
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_raw_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"state": "idle"}


def _write_state(state_path: Path, data: dict) -> None:
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _append_log(log_path: Path, text: str) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text)


def get_deploy_state(project_root: Path) -> DeployState:
    state_path = _state_path(project_root)
    raw = _read_raw_state(state_path)
    if raw.get("state") == "running":
        pid = raw.get("pid")
        if pid and not _pid_alive(int(pid)):
            raw["state"] = "failed"
            raw["error"] = f"process {pid} disappeared"
            raw["finished_at"] = _now_iso()
            _write_state(state_path, raw)
    return DeployState(
        state=raw.get("state", "idle"),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
        error=raw.get("error"),
        last_step=raw.get("last_step"),
        smoke_status=raw.get("smoke_status", "skipped"),
    )


def _build_deploy_cmd(component: DeployComponent) -> str | None:
    if component.type == "docker":
        if not component.service:
            return None
        return f"docker compose up -d {component.service}"
    return component.command


def _run_smoke_tests(cwd: Path, log_path: Path) -> tuple[str, ActionResult | None]:
    """Run .ai-dev-factory/scripts/smoke.sh if present.

    Returns (smoke_status, failure_result).
    smoke_status: "skipped" | "success" | "failed"
    failure_result: None on success/skip, ActionResult(ok=False) on failure.
    """
    smoke_rel = ".ai-dev-factory/scripts/smoke.sh"
    smoke_path = cwd / smoke_rel
    if not smoke_path.exists():
        _append_log(log_path, f"\n--- smoke tests: {smoke_rel} not found, skipping ---\n")
        return "skipped", None

    _append_log(log_path, f"\n--- smoke tests: {smoke_rel} ---\n")
    try:
        result = subprocess.run(
            ["bash", smoke_rel],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        msg = "smoke tests timed out"
        _append_log(log_path, f"{msg}\n")
        return "failed", ActionResult(ok=False, message=msg, error=msg)

    if result.stdout:
        _append_log(log_path, result.stdout)
    if result.stderr:
        _append_log(log_path, result.stderr)

    if result.returncode == 0:
        _append_log(log_path, "smoke tests passed\n")
        return "success", None

    msg = f"smoke tests failed (exit {result.returncode})"
    _append_log(log_path, f"{msg}\n")
    return "failed", ActionResult(ok=False, message=msg, error=msg)


def _run_healthcheck(
    hc: DeployHealthcheck, cwd: Path, log_path: Path
) -> ActionResult:
    _append_log(log_path, f"\n--- healthcheck: {hc.command} ---\n")
    for attempt in range(1, hc.retries + 1):
        if attempt > 1:
            time.sleep(hc.delay)
        try:
            result = subprocess.run(
                hc.command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=hc.timeout,
            )
        except subprocess.TimeoutExpired:
            _append_log(log_path, f"healthcheck attempt {attempt}/{hc.retries} timed out\n")
            continue
        if result.stdout:
            _append_log(log_path, result.stdout)
        if result.stderr:
            _append_log(log_path, result.stderr)
        if result.returncode == 0:
            _append_log(log_path, "healthcheck passed\n")
            return ActionResult(ok=True, message="healthcheck passed")
        _append_log(log_path, f"healthcheck attempt {attempt}/{hc.retries} failed (exit {result.returncode})\n")
    msg = f"healthcheck failed after {hc.retries} attempt(s)"
    return ActionResult(ok=False, message=msg, error=msg)


def _inject_compose_flags(cmd: str, compose_project: str, env_file: str) -> str:
    """Prepend -p / --env-file isolation flags to a docker compose command."""
    if not cmd.startswith("docker compose "):
        return cmd
    suffix = cmd[len("docker compose "):]
    return f"docker compose -p {compose_project} --env-file {env_file} {suffix}"


def _do_deploy(
    project_id: str,
    project_root: Path,
    sandbox: SandboxState | None = None,
) -> ActionResult:
    if sandbox is not None:
        sandbox_dir = Path(sandbox.env_file).parent
        state_path = sandbox_dir / "state.json"
        log_path = sandbox_dir / "logs" / "deploy.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cwd = Path(sandbox.worktree_path) if sandbox.worktree_path else project_root
    else:
        state_path = _state_path(project_root)
        log_path = _log_path(project_root)
        cwd = project_root

    profile = _load_deploy_profile(cwd)
    if profile is None:
        return ActionResult(ok=False, message="no deploy.yml found")

    pid = os.getpid()
    started_at = _now_iso()

    _write_state(state_path, {
        "state": "running", "pid": pid,
        "started_at": started_at, "finished_at": None,
        "error": None, "last_step": None,
    })
    _append_log(log_path, f"\n=== deploy started {started_at} ===\n")

    for component in profile.components:
        _write_state(state_path, {
            "state": "running", "pid": pid,
            "started_at": started_at, "finished_at": None,
            "error": None, "last_step": component.name,
        })
        _append_log(log_path, f"\n--- component: {component.name} ({component.type}) ---\n")

        cmd = _build_deploy_cmd(component)
        if cmd is None:
            msg = f"component {component.name!r}: no command or service defined"
            _append_log(log_path, msg + "\n")
            finished_at = _now_iso()
            _write_state(state_path, {
                "state": "failed", "pid": pid,
                "started_at": started_at, "finished_at": finished_at,
                "error": msg, "last_step": component.name,
            })
            return ActionResult(ok=False, message=msg, error=msg)

        if sandbox is not None:
            cmd = _inject_compose_flags(cmd, sandbox.compose_project, sandbox.env_file)

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=str(cwd)
        )
        if result.stdout:
            _append_log(log_path, result.stdout)
        if result.stderr:
            _append_log(log_path, result.stderr)

        if result.returncode != 0:
            msg = f"component {component.name!r} failed (exit {result.returncode}): {result.stderr.strip()[:200]}"
            finished_at = _now_iso()
            _write_state(state_path, {
                "state": "failed", "pid": pid,
                "started_at": started_at, "finished_at": finished_at,
                "error": msg, "last_step": component.name,
            })
            return ActionResult(
                ok=False, message=msg, error=msg,
                returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
            )

    if profile.healthcheck:
        hc_result = _run_healthcheck(profile.healthcheck, cwd, log_path)
        if not hc_result.ok:
            finished_at = _now_iso()
            _write_state(state_path, {
                "state": "failed", "pid": pid,
                "started_at": started_at, "finished_at": finished_at,
                "error": hc_result.message, "last_step": "healthcheck",
                "smoke_status": "skipped",
            })
            return hc_result

    smoke_status, smoke_failure = _run_smoke_tests(cwd, log_path)
    if smoke_failure is not None:
        finished_at = _now_iso()
        _write_state(state_path, {
            "state": "failed", "pid": pid,
            "started_at": started_at, "finished_at": finished_at,
            "error": smoke_failure.message, "last_step": "smoke",
            "smoke_status": smoke_status,
        })
        return smoke_failure

    finished_at = _now_iso()
    _write_state(state_path, {
        "state": "success", "pid": pid,
        "started_at": started_at, "finished_at": finished_at,
        "error": None, "last_step": None,
        "smoke_status": smoke_status,
    })
    _append_log(log_path, f"\n=== deploy finished {finished_at} ===\n")
    return ActionResult(ok=True, message="deploy completed successfully")


def run_deploy(project_id: str, project_root: Path) -> ActionResult:
    lock = _get_lock(project_id)
    if not lock.acquire(blocking=False):
        return ActionResult(ok=False, message="deploy already in progress", error="locked")
    try:
        return _do_deploy(project_id, project_root)
    finally:
        lock.release()


def run_deploy_sandboxed(
    project_id: str,
    project_root: Path,
    sandbox_manager: object,
    branch: str | None = None,
    job_type: str = "deploy",
) -> ActionResult:
    lock = _get_lock(project_id)
    if not lock.acquire(blocking=False):
        return ActionResult(ok=False, message="deploy already in progress", error="locked")
    sandbox = None
    try:
        try:
            sandbox = sandbox_manager.create_with_worktree(
                ticket_id=project_id,
                project_root=str(project_root),
                branch=branch,
                job_type=job_type,
            )
        except Exception as exc:
            return ActionResult(
                ok=False, message=f"sandbox creation failed: {exc}", error=str(exc)
            )
        return _do_deploy(project_id, project_root, sandbox=sandbox)
    finally:
        lock.release()
        if sandbox is not None:
            try:
                sandbox_manager.mark_completed(sandbox.id)
                sandbox_manager.cleanup_completed()
            except Exception as exc:
                logger.warning("sandbox cleanup after deploy failed: %s", exc)


def _do_restart(project_id: str, project_root: Path) -> ActionResult:
    profile = _load_deploy_profile(project_root)
    if profile is None:
        return ActionResult(ok=False, message="no deploy.yml found")

    state_path = _state_path(project_root)
    log_path = _log_path(project_root)
    pid = os.getpid()
    started_at = _now_iso()

    _write_state(state_path, {
        "state": "running", "pid": pid,
        "started_at": started_at, "finished_at": None,
        "error": None, "last_step": None,
    })
    _append_log(log_path, f"\n=== restart started {started_at} ===\n")

    for component in profile.components:
        _write_state(state_path, {
            "state": "running", "pid": pid,
            "started_at": started_at, "finished_at": None,
            "error": None, "last_step": component.name,
        })
        _append_log(log_path, f"\n--- restart component: {component.name} ({component.type}) ---\n")

        if component.type == "docker":
            if not component.service:
                continue
            cmd = f"docker compose restart {component.service}"
        else:
            cmd = component.command
            if not cmd:
                continue

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=str(project_root)
        )
        if result.stdout:
            _append_log(log_path, result.stdout)
        if result.stderr:
            _append_log(log_path, result.stderr)

        if result.returncode != 0:
            msg = f"component {component.name!r} restart failed (exit {result.returncode}): {result.stderr.strip()[:200]}"
            finished_at = _now_iso()
            _write_state(state_path, {
                "state": "failed", "pid": pid,
                "started_at": started_at, "finished_at": finished_at,
                "error": msg, "last_step": component.name,
            })
            return ActionResult(
                ok=False, message=msg, error=msg,
                returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
            )

    finished_at = _now_iso()
    _write_state(state_path, {
        "state": "success", "pid": pid,
        "started_at": started_at, "finished_at": finished_at,
        "error": None, "last_step": None,
    })
    _append_log(log_path, f"\n=== restart finished {finished_at} ===\n")
    return ActionResult(ok=True, message="restart completed successfully")


def run_restart(project_id: str, project_root: Path) -> ActionResult:
    lock = _get_lock(project_id)
    if not lock.acquire(blocking=False):
        return ActionResult(ok=False, message="deploy already in progress", error="locked")
    try:
        return _do_restart(project_id, project_root)
    finally:
        lock.release()


def get_deploy_logs(project_root: Path, lines: int) -> list[str]:
    log_path = _log_path(project_root)
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return all_lines[-lines:] if len(all_lines) > lines else all_lines
