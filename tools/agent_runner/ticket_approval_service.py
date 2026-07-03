"""Ticket Approval Service.

Human-in-the-loop execution approval workflow on top of the readiness state.

A ticket flagged ``ready_candidate`` by the readiness evaluator can be approved
or rejected for execution. Approvals append rows to ``ticket_approvals``
(append-only, no row is ever overwritten). Same-decision retries are idempotent
(no new row, no readiness mutation, no raise). Opposite-decision retries raise
``ValueError("contradictory_transition")`` — the API maps that to HTTP 409. Out
of context decisions (no prior decision and readiness is not ``ready_candidate``)
raise ``ValueError("invalid_state")`` — also 409.

The service writes ``readiness_status='ready_to_take'`` on approve and
``readiness_status='blocked'`` (with a rejection reason appended) on reject. It
never touches scheduler/worker code: ``ready_to_take`` is purely informational
for this ticket.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


_EXECUTION = "execution"
_PLAN = "plan"


def _serialize_row(row: dict) -> dict:
    """Return a stdlib-friendly copy of a DB row (no sqlite3.Row leakage)."""
    return dict(row)


def _rejection_reason(approved_by: str | None) -> str:
    who = approved_by or "unknown"
    return f"Execution approval rejected by {who}"


def request_execution_approval(db_path, ticket_id: str) -> dict:
    """Create a ``pending`` execution approval row, or return the existing pending one."""
    latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)
    if latest and latest.get("approval_status") == "pending":
        return _serialize_row(latest)
    runtime_db.insert_ticket_approval(
        db_path,
        ticket_id,
        approval_type=_EXECUTION,
        approval_status="pending",
        approved_by=None,
        approval_comment=None,
    )
    new_latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)
    return _serialize_row(new_latest)


def approve_execution(
    db_path,
    ticket_id: str,
    approved_by: str,
    comment: str | None = None,
) -> dict:
    """Approve execution for ``ticket_id``. See module docstring for semantics."""
    readiness = runtime_db.get_ticket_readiness(db_path, ticket_id)
    latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)

    if latest and latest.get("approval_status") == "approved":
        return _serialize_row(latest)
    if latest and latest.get("approval_status") == "rejected":
        raise ValueError("contradictory_transition")

    readiness_status = (readiness or {}).get("readiness_status")
    if readiness_status != "ready_candidate":
        raise ValueError("invalid_state")

    runtime_db.insert_ticket_approval(
        db_path,
        ticket_id,
        approval_type=_EXECUTION,
        approval_status="approved",
        approved_by=approved_by,
        approval_comment=comment,
    )
    runtime_db.upsert_ticket_readiness(
        db_path,
        ticket_id,
        readiness_status="ready_to_take",
        evaluated_at=runtime_db._now_iso(),
    )
    new_latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)
    return _serialize_row(new_latest)


def reject_execution(
    db_path,
    ticket_id: str,
    approved_by: str,
    comment: str | None = None,
) -> dict:
    """Reject execution for ``ticket_id``. See module docstring for semantics."""
    readiness = runtime_db.get_ticket_readiness(db_path, ticket_id)
    latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)

    if latest and latest.get("approval_status") == "rejected":
        return _serialize_row(latest)
    if latest and latest.get("approval_status") == "approved":
        raise ValueError("contradictory_transition")

    readiness_status = (readiness or {}).get("readiness_status")
    if readiness_status != "ready_candidate":
        raise ValueError("invalid_state")

    runtime_db.insert_ticket_approval(
        db_path,
        ticket_id,
        approval_type=_EXECUTION,
        approval_status="rejected",
        approved_by=approved_by,
        approval_comment=comment,
    )

    reason = _rejection_reason(approved_by)
    existing_reasons = list((readiness or {}).get("blocking_reasons_json") or [])
    if reason not in existing_reasons:
        existing_reasons.append(reason)
    runtime_db.upsert_ticket_readiness(
        db_path,
        ticket_id,
        readiness_status="blocked",
        ready_candidate=0,
        blocking_reasons_json=existing_reasons,
        evaluated_at=runtime_db._now_iso(),
    )

    new_latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)
    return _serialize_row(new_latest)


def get_ticket_approvals(db_path, ticket_id: str) -> list[dict]:
    """Append-only approval history for ``ticket_id`` (oldest first)."""
    return [_serialize_row(r) for r in runtime_db.list_ticket_approvals(db_path, ticket_id)]


def auto_approve_plan(
    db_path,
    ticket_id: str,
    *,
    reason: str = "PROJECT_SETTING",
) -> dict:
    """Insert a `plan` approval row marking the plan as auto-approved.

    Idempotent: if the latest `plan` approval for the ticket is already
    ``approved``, the existing row is returned without inserting a duplicate.
    """
    latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _PLAN)
    if latest and latest.get("approval_status") == "approved":
        return _serialize_row(latest)
    runtime_db.insert_ticket_approval(
        db_path,
        ticket_id,
        approval_type=_PLAN,
        approval_status="approved",
        approved_by="SYSTEM",
        approval_comment=reason,
    )
    new_latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _PLAN)
    return _serialize_row(new_latest)


def compute_execution_eligibility(db_path, ticket_id: str) -> str:
    """Return the effective execution eligibility state.

    Combines the persisted readiness row with the latest execution approval so
    re-running readiness evaluation does not demote an already-approved ticket
    back to ``ready_candidate``.
    """
    readiness = runtime_db.get_ticket_readiness(db_path, ticket_id)
    base_status = (readiness or {}).get("readiness_status") or "not_started"
    latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, _EXECUTION)
    if latest and latest.get("approval_status") == "approved" and base_status in {
        "ready_candidate",
        "ready_to_take",
    }:
        return "ready_to_take"
    if latest and latest.get("approval_status") == "rejected":
        return "blocked"
    return base_status
