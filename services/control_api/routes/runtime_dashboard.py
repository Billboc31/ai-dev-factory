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
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

router = APIRouter(prefix="/runtime-dashboard", tags=["runtime-dashboard"])
logger = logging.getLogger("control-api")

_ACTIVE_STATUSES = {"running", "creating", "active"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _project_root(request: Request) -> Path:
    return request.app.state.project_root


def _sandboxes_root(project_root: Path) -> Path:
    return project_root / "sandboxes"


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
    finished_at = raw.get("finished_at") or raw.get("completed_at")
    return SandboxRunSummary(
        id=sandbox_id,
        project_id=str(project_id),
        status=str(status),
        started_at=started_at,
        finished_at=finished_at,
        ports=raw.get("ports") or {},
        worktree_path=raw.get("worktree_path"),
        compose_project=raw.get("compose_project"),
    )


# ── sandbox runs ──────────────────────────────────────────────────────────────

@router.get("/sandbox-runs", response_model=list[SandboxRunSummary])
def list_sandbox_runs(request: Request) -> list[SandboxRunSummary]:
    root = _sandboxes_root(_project_root(request))
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
    root = _sandboxes_root(_project_root(request))
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
    root = _sandboxes_root(_project_root(request))
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

    return RuntimeHealth(
        supervisor_status=supervisor_status,
        active_jobs=active_jobs,
        stale_pid_files=stale_pid_files,
        stale_locks=stale_locks,
    )
