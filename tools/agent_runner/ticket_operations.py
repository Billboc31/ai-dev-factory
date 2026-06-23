"""Ticket Operations Service (T204).

Guarded manual recovery operations exposed through the Control API. Every
operation is operator-initiated, audited, and restricted to the existing runner
state machine.

Forbidden states: ``PLANNING``, ``CODING``, ``CANCELLED``. The service
defensively rejects any handler attempt to write a runner state outside the
existing ``VALID_RUNNER_STATES`` set.
"""

from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import ticket_approval_service  # noqa: E402
import ticket_diagnostics  # noqa: E402

# Imported lazily where needed to keep the service importable without optional
# heavy dependencies (e.g. supervisor / Postgres bindings).

# ── Runner state guardrails ──────────────────────────────────────────────────

VALID_RUNNER_STATES: frozenset[str] = frozenset({
    "INIT",
    "PLAN_REVIEW_NEEDED",
    "PLAN_FIX_REQUIRED",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_FIX_REQUIRED",
    "IMPLEMENTATION_APPROVED",
    "TEST_COMPLETE",
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})

FORBIDDEN_RUNNER_STATES: frozenset[str] = frozenset({
    "PLANNING",
    "CODING",
    "CANCELLED",
})

_HEARTBEAT_FRESH_SECONDS = 120


# ── Spec dataclass ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OperationSpec:
    """Describes one ticket operation.

    ``handler`` receives ``(ctx)`` where ctx exposes the resolved environment
    (db_path, project_root, worktrees_dir, ticket_id, project_id, payload,
    requested_by). It must return a dict with at least ``message`` and may set
    ``details``. Handlers raise ``OperationError`` to reject preconditions.
    """

    key: str
    label: str
    group: str
    safety_level: str
    requires_reason: bool = False
    requires_typed_ticket_id: bool = False
    requires_double_confirmation: bool = False
    handler: Callable[["OperationContext"], dict] = field(default=lambda ctx: {"message": "ok"})


@dataclass
class OperationContext:
    db_path: Any
    project_root: Path
    worktrees_dir: Path | None
    ticket_id: str
    project_id: str | None
    payload: dict
    requested_by: str


class OperationError(Exception):
    """Raised by handlers to signal a controlled rejection.

    ``status_code`` is the HTTP code the route layer should surface.
    Rejected attempts are still audited.
    """

    def __init__(self, message: str, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts_for_archive() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_run_dir(project_root: Path, ticket_id: str, worktrees_dir: Path | None) -> Path:
    if worktrees_dir is not None:
        candidate = worktrees_dir / ticket_id / "runs" / ticket_id
        if (candidate / "state.json").exists():
            return candidate
    return project_root / "runs" / ticket_id


def _read_state(run_dir: Path) -> dict:
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(run_dir: Path, data: dict) -> None:
    state_value = data.get("state")
    if state_value is not None:
        if state_value not in VALID_RUNNER_STATES:
            raise OperationError(
                f"refusing to write invalid runner state {state_value!r}",
                status_code=500,
            )
    state_file = run_dir / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["updated_at"] = _now_iso()
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_iso(value: str | None) -> float | None:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return None


def _heartbeat_is_fresh(heartbeat_at: str | None) -> bool:
    epoch = _parse_iso(heartbeat_at)
    if epoch is None:
        return False
    import time
    return (time.time() - epoch) < _HEARTBEAT_FRESH_SECONDS


def _worker_row(db_path: Any, ticket_id: str) -> dict | None:
    try:
        for w in runtime_db.list_workers(db_path) or []:
            if w.get("ticket_id") == ticket_id:
                return w
    except Exception:
        return None
    return None


def _ticket_archived(run_dir: Path) -> bool:
    return bool(_read_state(run_dir).get("archived"))


def _safe_run(cmd: list[str], cwd: Path | None = None, timeout: float = 30) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout,
            cwd=str(cwd) if cwd is not None else None,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _read_ticket_content(run_dir: Path) -> str:
    ticket_path = run_dir / "ticket.md"
    if ticket_path.exists():
        try:
            return ticket_path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


# ── Handlers — advisory re-runs ──────────────────────────────────────────────

def _handle_rerun_intelligence(ctx: OperationContext) -> dict:
    run_dir = _resolve_run_dir(ctx.project_root, ctx.ticket_id, ctx.worktrees_dir)
    ticket_content = _read_ticket_content(run_dir)
    if not ticket_content:
        raise OperationError("ticket content not available")
    import ticket_intelligence_analyzer as _analyzer
    _analyzer.run_analysis(
        ctx.db_path,
        ctx.ticket_id,
        ticket_content,
        "claude --dangerously-skip-permissions",
        ctx.project_root,
    )
    return {"message": "Intelligence analysis re-run completed."}


def _handle_rerun_readiness(ctx: OperationContext) -> dict:
    run_dir = _resolve_run_dir(ctx.project_root, ctx.ticket_id, ctx.worktrees_dir)
    ticket_content = _read_ticket_content(run_dir)
    if not ticket_content:
        raise OperationError("ticket content not available")
    import ticket_readiness_evaluator as _evaluator
    _evaluator.run_evaluation(ctx.db_path, ctx.ticket_id, ticket_content, ctx.project_root)
    return {"message": "Readiness evaluation re-run completed."}


def _handle_rerun_rules(ctx: OperationContext) -> dict:
    if not ctx.project_id:
        raise OperationError("project_id is required to evaluate execution rules")
    import execution_rules_engine as _rules
    result = _rules.evaluate_ticket(ctx.db_path, ctx.project_id, ctx.ticket_id)
    return {
        "message": "Execution rules evaluation completed.",
        "details": {"eligibility_status": result.get("eligibility_status")},
    }


def _handle_rerun_diagnostics(ctx: OperationContext) -> dict:
    result = ticket_diagnostics.diagnose_ticket(
        ctx.db_path,
        ctx.project_root,
        ctx.ticket_id,
        worktrees_dir=ctx.worktrees_dir,
        project_id=ctx.project_id,
    )
    return {
        "message": "Diagnostics re-run completed.",
        "details": {
            "is_stuck": bool(result.get("is_stuck")),
            "severity": result.get("severity"),
        },
    }


# ── Handlers — approval delegation ───────────────────────────────────────────

def _handle_approve_execution(ctx: OperationContext) -> dict:
    try:
        ticket_approval_service.approve_execution(
            ctx.db_path,
            ctx.ticket_id,
            approved_by=ctx.requested_by,
            comment=ctx.payload.get("reason"),
        )
    except ValueError as exc:
        raise OperationError(str(exc), status_code=409) from exc
    return {"message": "Execution approved."}


def _handle_reject_execution(ctx: OperationContext) -> dict:
    try:
        ticket_approval_service.reject_execution(
            ctx.db_path,
            ctx.ticket_id,
            approved_by=ctx.requested_by,
            comment=ctx.payload.get("reason"),
        )
    except ValueError as exc:
        raise OperationError(str(exc), status_code=409) from exc
    return {"message": "Execution rejected."}


# ── Handlers — recovery actions ──────────────────────────────────────────────

def _handle_mark_blocked(ctx: OperationContext) -> dict:
    reason = (ctx.payload.get("reason") or "").strip()
    if not reason:
        raise OperationError("reason is required")
    existing = runtime_db.get_ticket_readiness(ctx.db_path, ctx.ticket_id)
    existing_reasons = list((existing or {}).get("blocking_reasons_json") or [])
    formatted = f"manual: {reason} (by {ctx.requested_by})"
    if formatted not in existing_reasons:
        existing_reasons.append(formatted)
    runtime_db.upsert_ticket_readiness(
        ctx.db_path,
        ctx.ticket_id,
        readiness_status="blocked",
        ready_candidate=0,
        blocking_reasons_json=existing_reasons,
        evaluated_at=_now_iso(),
    )
    return {
        "message": "Ticket marked as blocked.",
        "details": {"reason": reason, "blocking_reasons_count": len(existing_reasons)},
    }


_RESET_TO_PLANNING_ARTIFACTS = ("plan.md", "reviews", "tests", "conflict", "retry-state.json")


def _archive_artifacts(run_dir: Path, artifacts: tuple[str, ...]) -> tuple[Path, list[str]]:
    archive_root = run_dir / "archive" / _ts_for_archive()
    archive_root.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for name in artifacts:
        src = run_dir / name
        if not src.exists():
            continue
        dst = archive_root / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append(name)
    return archive_root, moved


def _write_reset_metadata(
    archive_root: Path,
    operation_key: str,
    ticket_id: str,
    requested_by: str,
    reason: str,
    previous_state: str | None,
    new_state: str,
) -> None:
    meta = {
        "operation": operation_key,
        "ticket_id": ticket_id,
        "requested_by": requested_by,
        "reason": reason,
        "previous_state": previous_state,
        "new_state": new_state,
        "created_at": _now_iso(),
    }
    (archive_root / "reset.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _handle_reset_to_planning(ctx: OperationContext) -> dict:
    reason = (ctx.payload.get("reason") or "").strip()
    if not reason:
        raise OperationError("reason is required")
    run_dir = _resolve_run_dir(ctx.project_root, ctx.ticket_id, ctx.worktrees_dir)
    if not run_dir.exists():
        raise OperationError(f"run dir not found for {ctx.ticket_id}")
    state_data = _read_state(run_dir)
    previous_state = state_data.get("state")
    archive_root, moved = _archive_artifacts(run_dir, _RESET_TO_PLANNING_ARTIFACTS)
    new_state = "INIT"
    _write_reset_metadata(
        archive_root, "reset_to_planning", ctx.ticket_id, ctx.requested_by,
        reason, previous_state, new_state,
    )
    state_data["state"] = new_state
    _write_state(run_dir, state_data)
    try:
        runtime_db.upsert_ticket_runtime(ctx.db_path, ctx.ticket_id, state=new_state)
    except Exception:
        pass
    return {
        "message": "Ticket reset to planning and previous artifacts archived.",
        "details": {
            "archive_dir": str(archive_root),
            "archived_artifacts": moved,
            "previous_state": previous_state,
            "new_state": new_state,
        },
    }


_RESET_TO_CODING_ARTIFACTS = (
    "implementation-output.md",
    "reviews",
    "tests",
    "conflict",
    "retry-state.json",
)


def _handle_reset_to_coding(ctx: OperationContext) -> dict:
    reason = (ctx.payload.get("reason") or "").strip()
    if not reason:
        raise OperationError("reason is required")
    run_dir = _resolve_run_dir(ctx.project_root, ctx.ticket_id, ctx.worktrees_dir)
    if not run_dir.exists():
        raise OperationError(f"run dir not found for {ctx.ticket_id}")
    state_data = _read_state(run_dir)
    previous_state = state_data.get("state")
    archive_root, moved = _archive_artifacts(run_dir, _RESET_TO_CODING_ARTIFACTS)
    new_state = "PLAN_APPROVED"
    _write_reset_metadata(
        archive_root, "reset_to_coding", ctx.ticket_id, ctx.requested_by,
        reason, previous_state, new_state,
    )
    state_data["state"] = new_state
    _write_state(run_dir, state_data)
    try:
        runtime_db.upsert_ticket_runtime(ctx.db_path, ctx.ticket_id, state=new_state)
    except Exception:
        pass
    return {
        "message": "Ticket reset to coding and previous implementation artifacts archived.",
        "details": {
            "archive_dir": str(archive_root),
            "archived_artifacts": moved,
            "previous_state": previous_state,
            "new_state": new_state,
        },
    }


def _handle_clear_stuck_state(ctx: OperationContext) -> dict:
    worker = _worker_row(ctx.db_path, ctx.ticket_id)
    if worker is None:
        return {
            "message": "No stale worker row was present.",
            "details": {"cleared": False},
        }
    heartbeat_at = worker.get("heartbeat_at") or worker.get("started_at")
    if _heartbeat_is_fresh(heartbeat_at):
        raise OperationError(
            "refusing to clear: worker heartbeat is fresh",
            status_code=409,
            details={"heartbeat_at": heartbeat_at},
        )
    cleared = {
        "pid": worker.get("pid"),
        "worktree_path": worker.get("worktree_path"),
        "status": worker.get("status"),
        "heartbeat_at": heartbeat_at,
    }
    runtime_db.remove_worker(ctx.db_path, ctx.ticket_id)
    return {"message": "Stale worker row cleared.", "details": {"cleared": True, **cleared}}


def _handle_delete_worktree(ctx: OperationContext) -> dict:
    if not ctx.payload.get("confirm"):
        raise OperationError("confirm=true is required for destructive operations")
    if ctx.worktrees_dir is None:
        raise OperationError("worktrees root is not configured")
    worktrees_root = Path(ctx.worktrees_dir).resolve()
    target = (worktrees_root / ctx.ticket_id).resolve()
    try:
        target.relative_to(worktrees_root)
    except ValueError as exc:
        raise OperationError(
            f"refusing: target {target} is outside worktrees root {worktrees_root}",
            status_code=400,
        ) from exc
    if not target.exists():
        return {"message": "Worktree already absent.", "details": {"deleted_path": None}}
    worker = _worker_row(ctx.db_path, ctx.ticket_id)
    if worker is not None:
        heartbeat = worker.get("heartbeat_at") or worker.get("started_at")
        if _heartbeat_is_fresh(heartbeat):
            raise OperationError(
                "refusing: worker heartbeat is fresh",
                status_code=409,
                details={"heartbeat_at": heartbeat},
            )
    force = bool(ctx.payload.get("force"))
    status_proc = _safe_run(["git", "status", "--porcelain"], cwd=target)
    if status_proc is not None and status_proc.returncode == 0 and status_proc.stdout.strip() and not force:
        raise OperationError(
            "refusing: worktree has uncommitted changes (pass force=true to override)",
            status_code=409,
            details={"dirty": True},
        )
    git_args = ["git", "worktree", "remove"]
    if force:
        git_args.append("--force")
    git_args.append(str(target))
    proc = _safe_run(git_args, cwd=worktrees_root)
    git_ok = proc is not None and proc.returncode == 0
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    return {
        "message": "Worktree deleted.",
        "details": {
            "deleted_path": str(target),
            "git_worktree_remove_ok": git_ok,
            "git_stderr": (proc.stderr or "").strip() if proc is not None else None,
            "forced": force,
        },
    }


def _handle_archive_ticket(ctx: OperationContext) -> dict:
    reason = (ctx.payload.get("reason") or "").strip()
    if not reason:
        raise OperationError("reason is required")
    run_dir = _resolve_run_dir(ctx.project_root, ctx.ticket_id, ctx.worktrees_dir)
    if not run_dir.exists():
        raise OperationError(f"run dir not found for {ctx.ticket_id}")
    state_data = _read_state(run_dir)
    state_data["archived"] = True
    state_data["archived_reason"] = reason
    state_data["archived_by"] = ctx.requested_by
    state_data["archived_at"] = _now_iso()
    _write_state(run_dir, state_data)
    return {
        "message": "Ticket archived. Artifacts preserved.",
        "details": {
            "archived_reason": reason,
            "archived_by": ctx.requested_by,
            "archived_at": state_data["archived_at"],
        },
    }


# ── Registry ─────────────────────────────────────────────────────────────────

OPERATIONS: dict[str, OperationSpec] = {
    "rerun_intelligence": OperationSpec(
        key="rerun_intelligence",
        label="Re-run intelligence analysis",
        group="advisory",
        safety_level="low",
        handler=_handle_rerun_intelligence,
    ),
    "rerun_readiness": OperationSpec(
        key="rerun_readiness",
        label="Re-run readiness evaluation",
        group="advisory",
        safety_level="low",
        handler=_handle_rerun_readiness,
    ),
    "rerun_rules": OperationSpec(
        key="rerun_rules",
        label="Re-run execution rules",
        group="advisory",
        safety_level="low",
        handler=_handle_rerun_rules,
    ),
    "rerun_diagnostics": OperationSpec(
        key="rerun_diagnostics",
        label="Re-run diagnostics",
        group="advisory",
        safety_level="low",
        handler=_handle_rerun_diagnostics,
    ),
    "approve_execution": OperationSpec(
        key="approve_execution",
        label="Approve execution",
        group="approval",
        safety_level="medium",
        handler=_handle_approve_execution,
    ),
    "reject_execution": OperationSpec(
        key="reject_execution",
        label="Reject execution",
        group="approval",
        safety_level="medium",
        handler=_handle_reject_execution,
    ),
    "mark_blocked": OperationSpec(
        key="mark_blocked",
        label="Mark ticket blocked",
        group="recovery",
        safety_level="medium",
        requires_reason=True,
        handler=_handle_mark_blocked,
    ),
    "reset_to_planning": OperationSpec(
        key="reset_to_planning",
        label="Reset ticket to planning",
        group="recovery",
        safety_level="high",
        requires_reason=True,
        requires_typed_ticket_id=True,
        handler=_handle_reset_to_planning,
    ),
    "reset_to_coding": OperationSpec(
        key="reset_to_coding",
        label="Reset ticket to coding",
        group="recovery",
        safety_level="high",
        requires_reason=True,
        requires_typed_ticket_id=True,
        handler=_handle_reset_to_coding,
    ),
    "clear_stuck_state": OperationSpec(
        key="clear_stuck_state",
        label="Clear stale worker state",
        group="recovery",
        safety_level="medium",
        handler=_handle_clear_stuck_state,
    ),
    "delete_worktree": OperationSpec(
        key="delete_worktree",
        label="Delete ticket worktree",
        group="dangerous",
        safety_level="destructive",
        requires_typed_ticket_id=True,
        requires_double_confirmation=True,
        handler=_handle_delete_worktree,
    ),
    "archive_ticket": OperationSpec(
        key="archive_ticket",
        label="Archive ticket",
        group="dangerous",
        safety_level="medium",
        requires_reason=True,
        handler=_handle_archive_ticket,
    ),
}


# ── Listing operations ───────────────────────────────────────────────────────

def _compute_availability(
    spec: OperationSpec,
    *,
    runtime_row: dict | None,
    worker_row: dict | None,
    run_dir: Path,
    worktrees_dir: Path | None,
    ticket_id: str,
) -> tuple[bool, str | None]:
    """Return (enabled, disabled_reason) for ``spec``.

    Conservative: when in doubt, leave the operation enabled — the handler
    will enforce its own preconditions.
    """
    archived = _ticket_archived(run_dir)
    if archived and spec.key != "archive_ticket":
        return False, "Ticket is archived."

    if spec.key == "clear_stuck_state":
        if worker_row is None:
            return False, "No worker row to clear."
        if _heartbeat_is_fresh(worker_row.get("heartbeat_at")):
            return False, "Worker heartbeat is fresh."
        return True, None

    if spec.key == "delete_worktree":
        if worktrees_dir is None:
            return False, "Worktrees root not configured."
        target = worktrees_dir / ticket_id
        if not target.exists():
            return False, "Worktree does not exist."
        if worker_row is not None and _heartbeat_is_fresh(
            worker_row.get("heartbeat_at") or worker_row.get("started_at")
        ):
            return False, "Worker heartbeat is fresh."
        return True, None

    if spec.key in {"reset_to_planning", "reset_to_coding"}:
        if worker_row is not None and _heartbeat_is_fresh(
            worker_row.get("heartbeat_at") or worker_row.get("started_at")
        ):
            return False, "Worker heartbeat is fresh."
        return True, None

    return True, None


def list_operations(
    db_path: Any,
    project_root: Path,
    ticket_id: str,
    project_id: str | None = None,
    worktrees_dir: Path | None = None,
) -> list[dict]:
    """Return descriptors for every registered operation."""
    runtime_row = None
    try:
        runtime_row = runtime_db.get_ticket_runtime(db_path, ticket_id)
    except Exception:
        runtime_row = None
    worker_row = _worker_row(db_path, ticket_id)
    run_dir = _resolve_run_dir(project_root, ticket_id, worktrees_dir)

    out: list[dict] = []
    for spec in OPERATIONS.values():
        enabled, reason = _compute_availability(
            spec,
            runtime_row=runtime_row,
            worker_row=worker_row,
            run_dir=run_dir,
            worktrees_dir=worktrees_dir,
            ticket_id=ticket_id,
        )
        out.append({
            "operation_key": spec.key,
            "label": spec.label,
            "group": spec.group,
            "safety_level": spec.safety_level,
            "enabled": enabled,
            "disabled_reason": reason,
            "requires_reason": spec.requires_reason,
            "requires_typed_ticket_id": spec.requires_typed_ticket_id,
            "requires_double_confirmation": spec.requires_double_confirmation,
        })
    return out


# ── Confirmation validation ──────────────────────────────────────────────────

def _validate_confirmation(spec: OperationSpec, ticket_id: str, payload: dict) -> None:
    if spec.requires_reason:
        reason = (payload.get("reason") or "").strip()
        if not reason:
            raise OperationError("reason is required")
    if spec.requires_typed_ticket_id:
        typed = (payload.get("typed_ticket_id") or "").strip()
        if typed != ticket_id:
            raise OperationError("typed_ticket_id does not match ticket id")
    if spec.requires_double_confirmation:
        if not payload.get("confirm"):
            raise OperationError("confirm=true is required for destructive operations")


# ── Execute ──────────────────────────────────────────────────────────────────

def _audit(
    db_path: Any,
    *,
    ticket_id: str,
    project_id: str | None,
    operation_key: str,
    status: str,
    reason: str | None,
    requested_by: str,
    details: dict | None,
) -> None:
    """Best-effort audit. A failure here must never mask the operation result."""
    try:
        runtime_db.append_ticket_operation_audit(
            db_path,
            ticket_id,
            project_id,
            operation_key,
            status,
            reason=reason,
            requested_by=requested_by,
            details=details,
        )
    except Exception:
        pass
    try:
        runtime_db.append_runtime_event(
            db_path,
            ticket_id,
            f"operation:{operation_key}",
            f"{status}: {operation_key} by {requested_by}",
            metadata={"status": status, "requested_by": requested_by, "details": details or {}},
        )
    except Exception:
        pass


def execute_operation(
    db_path: Any,
    project_root: Path,
    ticket_id: str,
    operation_key: str,
    payload: dict | None = None,
    requested_by: str = "operator",
    project_id: str | None = None,
    worktrees_dir: Path | None = None,
) -> dict:
    """Validate, execute, and audit one operation. Always returns a dict.

    Raises ``OperationError`` for validation / handler rejections; the route
    layer maps ``OperationError`` to HTTP and records the rejection.
    """
    spec = OPERATIONS.get(operation_key)
    if spec is None:
        raise OperationError(f"unknown operation {operation_key!r}", status_code=404)

    payload = dict(payload or {})
    reason_value = payload.get("reason")

    try:
        _validate_confirmation(spec, ticket_id, payload)
    except OperationError as exc:
        _audit(
            db_path,
            ticket_id=ticket_id, project_id=project_id, operation_key=operation_key,
            status="rejected", reason=reason_value, requested_by=requested_by,
            details={"validation_error": exc.message, **(exc.details or {})},
        )
        raise

    ctx = OperationContext(
        db_path=db_path,
        project_root=project_root,
        worktrees_dir=worktrees_dir,
        ticket_id=ticket_id,
        project_id=project_id,
        payload=payload,
        requested_by=requested_by,
    )

    try:
        handler_result = spec.handler(ctx) or {}
    except OperationError as exc:
        _audit(
            db_path,
            ticket_id=ticket_id, project_id=project_id, operation_key=operation_key,
            status="rejected", reason=reason_value, requested_by=requested_by,
            details={"handler_error": exc.message, **(exc.details or {})},
        )
        raise
    except Exception as exc:  # noqa: BLE001
        _audit(
            db_path,
            ticket_id=ticket_id, project_id=project_id, operation_key=operation_key,
            status="error", reason=reason_value, requested_by=requested_by,
            details={"unexpected_error": repr(exc)},
        )
        raise OperationError(f"operation failed: {exc}", status_code=500) from exc

    message = handler_result.get("message") or "Operation completed."
    details = handler_result.get("details") or {}

    # Post-condition guardrail: any runner state we may have written must be in
    # the allowed set. We re-read state.json to catch accidental drift.
    run_dir = _resolve_run_dir(project_root, ticket_id, worktrees_dir)
    state_data = _read_state(run_dir)
    state_value = state_data.get("state")
    if state_value and state_value not in VALID_RUNNER_STATES:
        _audit(
            db_path,
            ticket_id=ticket_id, project_id=project_id, operation_key=operation_key,
            status="error", reason=reason_value, requested_by=requested_by,
            details={"invalid_runner_state_written": state_value},
        )
        raise OperationError(
            f"post-condition violated: invalid runner state {state_value!r}",
            status_code=500,
        )

    _audit(
        db_path,
        ticket_id=ticket_id, project_id=project_id, operation_key=operation_key,
        status="completed", reason=reason_value, requested_by=requested_by,
        details=details,
    )

    return {
        "ticket_id": ticket_id,
        "operation_key": operation_key,
        "status": "completed",
        "message": message,
        "details": details,
    }


__all__ = [
    "OPERATIONS",
    "OperationSpec",
    "OperationContext",
    "OperationError",
    "VALID_RUNNER_STATES",
    "FORBIDDEN_RUNNER_STATES",
    "list_operations",
    "execute_operation",
]
