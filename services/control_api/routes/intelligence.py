"""Ticket Intelligence routes — GET + POST /tickets/{ticket_id}/intelligence[/analyze]."""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import sys
import threading
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import TicketIntelligence, TicketIntelligenceQueued
from ..services.artifact_reader import get_ticket
from ..services.runtime_resolver import resolve_runs_dir, resolve_ticket_run_dir, resolve_worktrees_dir

try:
    from ..services.container_paths import _in_docker as _api_in_docker, to_container_path
except ImportError:
    def _api_in_docker() -> bool:
        return os.environ.get("AI_DEV_FACTORY_API_IN_DOCKER", "").strip().lower() in ("1", "true", "yes")

    def to_container_path(path: Path | str | None) -> Path | None:  # type: ignore[misc]
        return Path(path) if path is not None else None

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402
import ticket_intelligence_analyzer as _analyzer  # noqa: E402
import ticket_intelligence_recovery as _recovery  # noqa: E402

logger = logging.getLogger("control-api")
_intel_log = logging.getLogger("intel")
router = APIRouter(prefix="/tickets", tags=["intelligence"])
project_router = APIRouter(prefix="/projects", tags=["intelligence"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _exec_cmd(request: Request) -> str:
    return getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")


def _supervisor_url() -> str:
    return os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "http://host.docker.internal:8090").rstrip("/")


def _needs_host_exec(request: Request) -> bool:
    """True when claude must run on the host (Docker API or binary missing in PATH)."""
    if _api_in_docker():
        return True
    parts = shlex.split(_exec_cmd(request))
    if not parts:
        return False
    return shutil.which(parts[0]) is None


def _resolve_db_for_project(request: Request, project_id: str | None):
    """Return the project-scoped DB handle, falling back to the global one.

    Uses the persisted ``project_runtime_root`` from the registry when available
    (mapped for Docker), so the API reads the same SQLite file the supervisor
    writes on the host. Falls back to ``app.state.db_path`` when the resolved
    path is missing (single-project dev setups and tests).
    """
    if not project_id:
        return _db_path(request)

    project_runtime_root = None
    registry = getattr(request.app.state, "project_registry", None)
    if registry is not None:
        prt = registry.resolve_runtime_root(project_id)
        if prt is not None:
            project_runtime_root = to_container_path(prt)

    runtime_configured = bool(
        project_runtime_root is not None
        or os.environ.get("RUNTIME_BASE_ROOT")
        or os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    )
    if not runtime_configured:
        return _db_path(request)

    try:
        db = runtime_db.resolve_db_path_for_project(project_id, project_runtime_root)
    except Exception:
        db = None

    if db is not None:
        if isinstance(db, Path):
            mapped = to_container_path(db)
            if mapped is not None and mapped.exists():
                return mapped
        elif getattr(db, "exists", lambda: True)():
            return db

    return _db_path(request)




def _sqlite_bind_mount_unsafe() -> bool:
    """True when the Docker API must not open the bind-mounted SQLite runtime file.

    Concurrent container + host access to WAL-mode SQLite on macOS bind mounts
    causes intermittent disk I/O errors and ``database disk image is malformed``.
    In that mode all intelligence DB reads/writes go through the host supervisor.
    Postgres uses a networked store and is safe from the API container.

  Only active when ``HOST_RUNTIME_ROOT`` is configured (production Docker stack).
    Unit tests may set ``AI_DEV_FACTORY_API_IN_DOCKER`` without a bind mount.
    """
    if not _api_in_docker():
        return False
    if os.environ.get("RUNTIME_DB_BACKEND", "sqlite").strip().lower() == "postgres":
        return False
    return bool(os.environ.get("HOST_RUNTIME_ROOT", "").strip())


def _delegate_get_intelligence_from_supervisor(project_id: str, ticket_id: str) -> TicketIntelligence:
    """Read ticket intelligence from the host supervisor (host-owned SQLite)."""
    url = f"{_supervisor_url()}/projects/{project_id}/tickets/{ticket_id}/intelligence"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="supervisor unreachable — cannot read ticket intelligence from host DB",
        ) from None
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="supervisor timed out reading ticket intelligence") from None

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"no intelligence analysis found for ticket {ticket_id}")
    if resp.status_code >= 400:
        try:
            payload = resp.json()
            detail = payload.get("detail") or payload.get("error") or resp.text[:300]
        except Exception:
            detail = resp.text[:300]
        raise HTTPException(status_code=503, detail=f"supervisor intelligence read failed: {detail}")
    return _parse_row(resp.json())


def _delegate_analyze_to_supervisor(project_id: str, ticket_id: str, exec_cmd: str) -> None:
    """Run ticket intelligence on the host supervisor where claude is installed."""
    url = f"{_supervisor_url()}/projects/{project_id}/tickets/{ticket_id}/intelligence/analyze"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json={"exec_cmd": exec_cmd})
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="supervisor unreachable — ticket intelligence must run on the host (claude is not in the API container)",
        ) from None
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="supervisor timed out starting ticket intelligence analysis") from None

    if resp.status_code >= 400:
        try:
            payload = resp.json()
            detail = payload.get("detail") or payload.get("error") or resp.text[:300]
        except Exception:
            detail = resp.text[:300]
        raise HTTPException(status_code=503, detail=f"supervisor analyze failed: {detail}")


def _persist_delegation_failure(db, ticket_id: str, summary: str) -> None:
    """Best-effort: ensure a row exists in ``failed`` after delegation fails.

    The reaper covers cases where the row was never written, but writing here
    too lets the next poll return ``failed`` immediately instead of waiting for
    the stale threshold.
    """
    if db is None:
        return
    try:
        runtime_db.upsert_ticket_intelligence(
            db, ticket_id,
            analysis_status="failed",
            analysis_summary=summary,
        )
    except Exception:
        logger.exception("intel: failed to persist delegation failure for %s", ticket_id)


def _try_reap(db, *, project_id: str | None, ticket_id: str | None) -> None:
    """Run the stale-analysis reaper without ever raising into the caller."""
    if db is None:
        return
    try:
        recovered = _recovery.reap_stale_intelligence(db)
    except Exception:
        logger.exception("intel: reaper failed for %s", ticket_id)
        return
    for row in recovered:
        _intel_log.info(
            "intel.reaped project_id=%s ticket_id=%s db_path=%s previous_status=%s age_seconds=%d",
            project_id, row.get("ticket_id"), db,
            row.get("previous_status"), row.get("age_seconds"),
        )


def _parse_row(row: dict) -> TicketIntelligence:
    """Convert a raw DB row to a TicketIntelligence schema, deserialising JSON fields."""
    def _parse_json_list(val) -> list:
        if not val:
            return []
        try:
            result = json.loads(val)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_json_dict(val) -> dict | None:
        if not val:
            return None
        try:
            result = json.loads(val)
            return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _bool_or_none(val) -> bool | None:
        if val is None:
            return None
        return bool(val)

    return TicketIntelligence(
        ticket_id=row["ticket_id"],
        analysis_status=row["analysis_status"],
        difficulty_score=row.get("difficulty_score"),
        difficulty_label=row.get("difficulty_label"),
        risk_score=row.get("risk_score"),
        risk_label=row.get("risk_label"),
        complexity_factors=_parse_json_list(row.get("complexity_factors")),
        computed_signals_json=_parse_json_dict(row.get("computed_signals_json")),
        recommended_model=row.get("recommended_model"),
        recommended_model_reason=row.get("recommended_model_reason"),
        estimated_input_tokens=row.get("estimated_input_tokens"),
        estimated_output_tokens=row.get("estimated_output_tokens"),
        estimated_cost_min=row.get("estimated_cost_min"),
        estimated_cost_max=row.get("estimated_cost_max"),
        cost_currency=row.get("cost_currency"),
        cost_estimate_status=row.get("cost_estimate_status"),
        queue_rank=row.get("queue_rank"),
        queue_reason=row.get("queue_reason"),
        dependency_hints=_parse_json_list(row.get("dependency_hints")),
        parallel_safe_candidate=_bool_or_none(row.get("parallel_safe_candidate")),
        requires_human_plan_review=_bool_or_none(row.get("requires_human_plan_review")),
        human_plan_review_reason=row.get("human_plan_review_reason"),
        requires_human_code_review=_bool_or_none(row.get("requires_human_code_review")),
        human_code_review_reason=row.get("human_code_review_reason"),
        autonomous_execution_recommendation=row.get("autonomous_execution_recommendation"),
        analysis_summary=row.get("analysis_summary"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        failed_at=row.get("failed_at"),
        failure_origin=row.get("failure_origin"),
        stage=row.get("stage"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _read_ticket_content(project_root: Path, ticket_id: str, worktrees_dir: Path | None) -> str:
    """Read ticket.md from the run directory, or return empty string if not found."""
    try:
        runs_dir = resolve_runs_dir(project_root)
        run_dir = resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir)
        ticket_path = run_dir / "ticket.md"
        if ticket_path.exists():
            return ticket_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("could not read ticket.md for %s: %s", ticket_id, exc)
    return ""


@router.get("/{ticket_id}/intelligence", response_model=TicketIntelligence)
def get_intelligence(
    ticket_id: str,
    request: Request,
    project_id: str | None = None,
) -> TicketIntelligence:
    logger.info("api: GET /tickets/%s/intelligence", ticket_id)
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    if _sqlite_bind_mount_unsafe():
        if not project_id:
            raise HTTPException(
                status_code=503,
                detail="ticket intelligence must be read on the host; use the project-scoped endpoint",
            )
        return _delegate_get_intelligence_from_supervisor(project_id, ticket_id)

    db = _resolve_db_for_project(request, project_id)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    # Opportunistic stale-analysis recovery — runs on every GET, but only
    # rewrites rows past STALE_QUEUED_SECONDS / STALE_RUNNING_SECONDS.
    _try_reap(db, project_id=project_id, ticket_id=ticket_id)

    row = runtime_db.get_ticket_intelligence(db, ticket_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"no intelligence analysis found for ticket {ticket_id}",
        )

    return _parse_row(row)


@router.post(
    "/{ticket_id}/intelligence/analyze",
    response_model=TicketIntelligenceQueued,
    status_code=202,
)
def analyze_intelligence(
    ticket_id: str,
    request: Request,
    project_id: str | None = None,
) -> TicketIntelligenceQueued:
    logger.info("api: POST /tickets/%s/intelligence/analyze", ticket_id)
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    exec_cmd = _exec_cmd(request)

    if _needs_host_exec(request):
        if not project_id:
            raise HTTPException(
                status_code=503,
                detail=(
                    "ticket intelligence must run on the host where claude is installed; "
                    "use the project-scoped analyze endpoint"
                ),
            )

        url = f"{_supervisor_url()}/projects/{project_id}/tickets/{ticket_id}/intelligence/analyze"
        db = None
        if not _sqlite_bind_mount_unsafe():
            db = _resolve_db_for_project(request, project_id)
            if db is None:
                raise HTTPException(status_code=503, detail="database not available")
            _try_reap(db, project_id=project_id, ticket_id=ticket_id)
            existing = runtime_db.get_ticket_intelligence(db, ticket_id)
            if existing and existing.get("analysis_status") in {"queued", "running"}:
                return TicketIntelligenceQueued(
                    ticket_id=ticket_id,
                    analysis_status=existing["analysis_status"],
                )

        _intel_log.info(
            "intel.delegated project_id=%s ticket_id=%s db_path=%s supervisor_url=%s",
            project_id, ticket_id, db, url,
        )
        logger.info(
            "api: delegating ticket intelligence %s/%s to supervisor (claude not available in API process)",
            project_id,
            ticket_id,
        )
        try:
            _delegate_analyze_to_supervisor(project_id, ticket_id, exec_cmd)
        except HTTPException as exc:
            if db is not None:
                _persist_delegation_failure(
                    db, ticket_id,
                    f"Supervisor delegation failed: {exc.detail}",
                )
            _intel_log.info(
                "intel.failed project_id=%s ticket_id=%s reason=delegation status=%d",
                project_id, ticket_id, exc.status_code,
            )
            raise
        return TicketIntelligenceQueued(ticket_id=ticket_id, analysis_status="queued")

    db = _resolve_db_for_project(request, project_id)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    _try_reap(db, project_id=project_id, ticket_id=ticket_id)

    existing = runtime_db.get_ticket_intelligence(db, ticket_id)
    if existing and existing.get("analysis_status") in {"queued", "running"}:
        return TicketIntelligenceQueued(ticket_id=ticket_id, analysis_status=existing["analysis_status"])

    ticket_content = _read_ticket_content(project_root, ticket_id, wt_dir)

    runtime_db.upsert_ticket_intelligence(db, ticket_id, analysis_status="queued")
    _intel_log.info(
        "intel.queued project_id=%s ticket_id=%s db_path=%s",
        project_id, ticket_id, db,
    )

    def _bg() -> None:
        try:
            _analyzer.run_analysis(
                db, ticket_id, ticket_content, exec_cmd, project_root,
                project_id=project_id,
            )
        except Exception as exc:
            logger.exception(
                "intelligence analysis background error for project_id=%s ticket_id=%s stage=bg_thread",
                project_id, ticket_id,
            )
            _intel_log.exception(
                "intel.bg_thread_crash project_id=%s ticket_id=%s db_path=%s detail=%s",
                project_id, ticket_id, db, exc,
            )
            # ``run_analysis`` is supposed to swallow + persist its own
            # exceptions. If something still escapes (programmer error, ImportError,
            # SystemExit subclass, etc.), persist failed here so the row never
            # stays in ``queued`` / ``running``.
            import traceback as _traceback
            from datetime import datetime, timezone
            failed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            tb = _traceback.format_exc()
            try:
                runtime_db.upsert_ticket_intelligence(
                    db, ticket_id,
                    analysis_status="failed",
                    analysis_summary=f"Background thread crashed: {exc}",
                    failed_at=failed_at,
                    failure_origin="bg_thread_crash",
                    stage="failed",
                )
            except Exception:
                logger.exception(
                    "intelligence: failed to persist bg-thread crash for %s",
                    ticket_id,
                )
            try:
                runtime_db.append_runtime_event(
                    db,
                    ticket_id,
                    "ticket_intelligence_analysis_failed",
                    f"ticket_intelligence bg-thread crashed ticket_id={ticket_id}",
                    metadata={
                        "project_id": project_id,
                        "stage": "failed",
                        "failure_origin": "bg_thread_crash",
                        "analysis_summary": f"Background thread crashed: {exc}",
                        "traceback": tb[-2048:] if tb else "",
                    },
                )
            except Exception:
                logger.exception(
                    "intelligence: failed to append bg-thread crash event for %s",
                    ticket_id,
                )

    t = threading.Thread(target=_bg, daemon=True)
    t.start()

    return TicketIntelligenceQueued(ticket_id=ticket_id, analysis_status="queued")


@project_router.get("/{project_id}/tickets/{ticket_id}/intelligence", response_model=TicketIntelligence)
def get_intelligence_project(project_id: str, ticket_id: str, request: Request) -> TicketIntelligence:
    return get_intelligence(ticket_id, request, project_id=project_id)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/intelligence/analyze",
    response_model=TicketIntelligenceQueued,
    status_code=202,
)
def analyze_intelligence_project(project_id: str, ticket_id: str, request: Request) -> TicketIntelligenceQueued:
    return analyze_intelligence(ticket_id, request, project_id=project_id)
