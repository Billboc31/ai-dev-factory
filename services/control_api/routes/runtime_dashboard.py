"""Routes for the runtime dashboard (T139).

Exposes read-only views of sandbox runs, proposal runs, runtime health,
and log tailing. All data is sourced generically from the project root
directory structure — no project-specific assumptions.

Safety contract: DELETE endpoints reject with 409 when the target run is
active (status "running"/"creating") or its daemon.lock holds a live PID.
Main runtime paths (runs/, sandboxes/) are never removed as a whole.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import urllib.error  # noqa: F401 (kept for clarity)
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from ..services.infra_service_manager import resolve_proxy_routes_dir
from ..services.proxy_manager import build_sandbox_urls
from ..services.runtime_resolver import get_project_name, get_project_sandbox_dir, get_sandbox_root
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError

router = APIRouter(prefix="/runtime-dashboard", tags=["runtime-dashboard"])
logger = logging.getLogger("control-api")

_ACTIVE_STATUSES = {"running", "creating", "active"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _project_root(request: Request) -> Path:
    return request.app.state.project_root


def _proposal_dir(project_root: Path) -> Path:
    return project_root / "runs" / "auto-fix" / "proposals"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _read_lock(lock_path: Path) -> dict | None:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _lock_is_live(lock_path: Path) -> bool:
    data = _read_lock(lock_path)
    if not data:
        return False
    pid = data.get("pid")
    return bool(pid and _is_pid_alive(int(pid)))


def _check_supervisor_status() -> str:
    url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/")
    if not url:
        return "unknown"
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as resp:
            return "up" if resp.status < 300 else "down"
    except Exception:
        return "down"


def _get_sandbox_manager(request: Request) -> SandboxManager:
    if not hasattr(request.app.state, "_sandbox_manager"):
        request.app.state._sandbox_manager = SandboxManager()
    return request.app.state._sandbox_manager


def _get_sandboxes_dir(request: Request) -> Path:
    return _get_sandbox_manager(request).sandboxes_dir


# ── models ────────────────────────────────────────────────────────────────────

class SandboxRunSummary(BaseModel):
    id: str
    project_id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    ports: dict[str, int] = {}
    worktree_path: str | None = None
    compose_project: str | None = None
    runtime_root: str | None = None
    uptime_seconds: float | None = None
    urls: dict[str, str] = {}
    ref: str | None = None
    proxy_ready: bool | None = None
    healthcheck_status: str | None = None
    smoke_status: str | None = None
    failing_step: str | None = None
    created_at: str | None = None
    last_checked_at: str | None = None


class ProposalRunSummary(BaseModel):
    proposal_id: str
    sandbox_id: str | None = None
    status: str
    changed_files_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None


class LogResponse(BaseModel):
    content: str
    next_offset: int


class RuntimeHealth(BaseModel):
    supervisor_status: str
    active_jobs: int
    stale_pid_files: list[str]
    stale_locks: list[str]
    sqlite_degraded: bool = False


class OverviewResponse(BaseModel):
    sandbox_root: str
    project_name: str
    project_sandbox_dir: str
    sandboxes: list[SandboxRunSummary]


# ── sandbox run parsing ───────────────────────────────────────────────────────

def _parse_sandbox_state(state_path: Path) -> SandboxRunSummary | None:
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    sandbox_id = state_path.parent.name
    project_id = raw.get("project_id") or raw.get("ticket_id") or raw.get("project_root", "")
    status = raw.get("state") or raw.get("status") or "unknown"
    started_at = raw.get("started_at") or raw.get("created_at")
    created_at = raw.get("created_at")
    finished_at = raw.get("finished_at") or raw.get("completed_at")
    uptime_seconds: float | None = None
    if status == "running" and started_at:
        try:
            t = datetime.fromisoformat(started_at)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            uptime_seconds = (datetime.now(timezone.utc) - t).total_seconds()
        except (ValueError, TypeError):
            pass

    urls: dict[str, str] = raw.get("urls") or {}
    if not urls:
        try:
            urls = build_sandbox_urls(sandbox_id)
        except Exception:
            pass

    proxy_ready: bool | None = None
    try:
        proxy_ready = (resolve_proxy_routes_dir() / f"{sandbox_id}.yml").exists()
    except Exception:
        pass

    healthcheck_status: str | None = None
    smoke_status: str | None = None
    failing_step: str | None = None
    last_checked_at: str | None = None
    try:
        v = json.loads((state_path.parent / "validation.json").read_text(encoding="utf-8"))
        healthcheck_status = v.get("healthcheck_status")
        smoke_status = v.get("smoke_status")
        failing_step = v.get("failing_step")
        last_checked_at = v.get("last_checked_at") or v.get("checked_at")
    except (OSError, json.JSONDecodeError):
        pass

    return SandboxRunSummary(
        id=sandbox_id,
        project_id=str(project_id),
        status=str(status),
        started_at=started_at,
        finished_at=finished_at,
        ports=raw.get("ports") or {},
        worktree_path=raw.get("worktree_path"),
        compose_project=raw.get("compose_project"),
        runtime_root=raw.get("sandbox_runtime_root") or None,
        uptime_seconds=uptime_seconds,
        urls=urls,
        ref=raw.get("ref") or raw.get("branch") or raw.get("commit"),
        proxy_ready=proxy_ready,
        healthcheck_status=healthcheck_status,
        smoke_status=smoke_status,
        failing_step=failing_step,
        created_at=created_at,
        last_checked_at=last_checked_at,
    )


# ── sandbox runs ──────────────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewResponse)
def get_overview(request: Request) -> OverviewResponse:
    sandboxes_dir = _get_sandboxes_dir(request)
    sandboxes = []
    if sandboxes_dir.exists():
        for state_file in sorted(sandboxes_dir.glob("*/state.json")):
            item = _parse_sandbox_state(state_file)
            if item is not None:
                sandboxes.append(item)
    return OverviewResponse(
        sandbox_root=str(get_sandbox_root()),
        project_name=get_project_name(),
        project_sandbox_dir=str(get_project_sandbox_dir()),
        sandboxes=sandboxes,
    )


@router.get("/sandbox-runs", response_model=list[SandboxRunSummary])
def list_sandbox_runs(request: Request) -> list[SandboxRunSummary]:
    root = _get_sandboxes_dir(request)
    if not root.exists():
        return []
    results = []
    for state_file in sorted(root.glob("*/state.json")):
        item = _parse_sandbox_state(state_file)
        if item is not None:
            results.append(item)
    return results


@router.get("/sandbox-runs/{sandbox_id}/logs", response_model=LogResponse)
def get_sandbox_run_logs(
    sandbox_id: str,
    request: Request,
    offset: int = Query(default=0, ge=0),
) -> LogResponse:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id")
    root = _get_sandboxes_dir(request)
    sandbox_dir = root / sandbox_id
    if not sandbox_dir.exists():
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")
    log_path = sandbox_dir / "run.log"
    if not log_path.exists():
        return LogResponse(content="", next_offset=0)
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        tail = content[offset:]
        return LogResponse(content=tail, next_offset=offset + len(tail))
    except OSError:
        return LogResponse(content="", next_offset=offset)


@router.delete("/sandbox-runs/{sandbox_id}", status_code=204)
def delete_sandbox_run(sandbox_id: str, request: Request) -> Response:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id")
    root = _get_sandboxes_dir(request)
    sandbox_dir = root / sandbox_id
    if not sandbox_dir.exists():
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")

    state_file = sandbox_dir / "state.json"
    if state_file.exists():
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            status = str(raw.get("state") or raw.get("status") or "")
            if status in _ACTIVE_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail=f"sandbox is active (status: {status}) — stop it before deleting",
                )
        except HTTPException:
            raise
        except (OSError, json.JSONDecodeError):
            pass

    lock_file = sandbox_dir / "daemon.lock"
    if lock_file.exists() and _lock_is_live(lock_file):
        raise HTTPException(
            status_code=409,
            detail="sandbox has a live process (daemon.lock) — stop it before deleting",
        )

    shutil.rmtree(sandbox_dir, ignore_errors=True)
    logger.info("runtime-dashboard: deleted sandbox run %s", sandbox_id)
    return Response(status_code=204)


@router.post("/sandbox-runs/{sandbox_id}/stop", response_model=SandboxRunSummary)
def stop_sandbox_run(sandbox_id: str, request: Request) -> SandboxRunSummary:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id")
    mgr = _get_sandbox_manager(request)
    try:
        mgr.stop(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")
    state_file = mgr.sandboxes_dir / sandbox_id / "state.json"
    item = _parse_sandbox_state(state_file)
    if item is None:
        raise HTTPException(status_code=500, detail="failed to read sandbox state after stop")
    logger.info("runtime-dashboard: stopped sandbox %s", sandbox_id)
    return item


@router.post("/sandbox-runs/{sandbox_id}/restart", response_model=SandboxRunSummary)
def restart_sandbox_run(sandbox_id: str, request: Request) -> SandboxRunSummary:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id")
    mgr = _get_sandbox_manager(request)
    try:
        mgr.restart(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")
    state_file = mgr.sandboxes_dir / sandbox_id / "state.json"
    item = _parse_sandbox_state(state_file)
    if item is None:
        raise HTTPException(status_code=500, detail="failed to read sandbox state after restart")
    logger.info("runtime-dashboard: restarted sandbox %s", sandbox_id)
    return item


# ── proposal run parsing ──────────────────────────────────────────────────────

def _parse_proposal_state(state_path: Path) -> ProposalRunSummary | None:
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    proposal_id = state_path.parent.name
    return ProposalRunSummary(
        proposal_id=raw.get("proposal_id", proposal_id),
        sandbox_id=raw.get("sandbox_id"),
        status=raw.get("status", "unknown"),
        changed_files_count=raw.get("changed_files_count", 0),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
    )


# ── proposal runs ─────────────────────────────────────────────────────────────

@router.get("/proposal-runs", response_model=list[ProposalRunSummary])
def list_proposal_runs(request: Request) -> list[ProposalRunSummary]:
    proposals_root = _proposal_dir(_project_root(request))
    if not proposals_root.exists():
        return []
    results = []
    for state_file in sorted(proposals_root.glob("*/state.json")):
        item = _parse_proposal_state(state_file)
        if item is not None:
            results.append(item)
    return results


@router.get("/proposal-runs/{proposal_id}")
def get_proposal_summary(proposal_id: str, request: Request) -> dict:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", proposal_id):
        raise HTTPException(status_code=400, detail="invalid proposal_id")
    proposals_root = _proposal_dir(_project_root(request))
    state_file = proposals_root / proposal_id / "state.json"
    if not state_file.exists():
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/proposal-runs/{proposal_id}", status_code=204)
def delete_proposal_run(proposal_id: str, request: Request) -> Response:
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", proposal_id):
        raise HTTPException(status_code=400, detail="invalid proposal_id")
    proposals_root = _proposal_dir(_project_root(request))
    proposal_dir = proposals_root / proposal_id
    if not proposal_dir.exists():
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")

    state_file = proposal_dir / "state.json"
    if state_file.exists():
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            status = str(raw.get("status", ""))
            if status in _ACTIVE_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail=f"proposal is active (status: {status}) — wait for it to complete",
                )
        except HTTPException:
            raise
        except (OSError, json.JSONDecodeError):
            pass

    shutil.rmtree(proposal_dir, ignore_errors=True)
    logger.info("runtime-dashboard: deleted proposal run %s", proposal_id)
    return Response(status_code=204)


# ── health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=RuntimeHealth)
def get_runtime_health(request: Request) -> RuntimeHealth:
    root = _project_root(request)
    runs_dir = root / "runs"

    supervisor_status = _check_supervisor_status()

    active_jobs = 0
    stale_locks: list[str] = []
    stale_pid_files: list[str] = []

    if runs_dir.exists():
        for lock_file in runs_dir.glob("*/daemon.lock"):
            data = _read_lock(lock_file)
            if data and isinstance(data.get("pid"), int):
                if _is_pid_alive(data["pid"]):
                    active_jobs += 1
                else:
                    stale_locks.append(str(lock_file.relative_to(root)))

        for pid_file in runs_dir.glob("*.pid"):
            data = _read_lock(pid_file)
            if data and isinstance(data.get("pid"), int) and not _is_pid_alive(data["pid"]):
                stale_pid_files.append(str(pid_file.relative_to(root)))

    # SQLite degraded detection: DB exists but is inaccessible
    sqlite_degraded = False
    try:
        from ..services.board_service import _try_load_runtime_db
        _, _, sqlite_degraded = _try_load_runtime_db(root)
    except Exception:
        sqlite_degraded = True

    return RuntimeHealth(
        supervisor_status=supervisor_status,
        active_jobs=active_jobs,
        stale_pid_files=stale_pid_files,
        stale_locks=stale_locks,
        sqlite_degraded=sqlite_degraded,
    )
