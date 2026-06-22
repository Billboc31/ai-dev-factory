"""Ticket Diagnostics Service.

Read-only diagnostic capability that explains why a given ticket is stuck and
recommends safe recovery actions. Persists the latest diagnostic per ticket but
never mutates ticket state, worktrees, branches, PRs, scheduler/worker rows or
runs any agent. Every Git/subprocess call is bounded; any failure collapses to
``unknown`` rather than raising.

Public entry point::

    diagnose_ticket(db_path, project_root, ticket_id, *,
                    worktrees_dir=None, timeout_s=5) -> dict

The returned dict matches the persisted schema (see ``ticket_diagnostics`` in
``runtime_db``) plus parsed ``checks`` and ``recommended_actions`` lists.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import ticket_approval_service  # noqa: E402


# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_TIMEOUT_S = 5
_STALE_INTELLIGENCE_SECONDS = 30 * 60  # 30 minutes
_LOG_MAX_BYTES = 256 * 1024  # 256 KB
_LOG_TAIL_LINES = 20

# Runtime states that imply the ticket is considered "done" (merged or
# functionally complete). Used by the PR check to recommend ``sync_ticket_state``
# when the PR is merged but the ticket has not been marked done.
_DONE_STATES = frozenset({"DONE", "MERGED", "ARCHIVED"})


# ── Recommended action catalog ───────────────────────────────────────────────

RECOMMENDED_ACTION_CATALOG: dict[str, dict[str, str]] = {
    "rerun_intelligence":   {"label": "Re-run intelligence analysis",          "risk": "low"},
    "rerun_readiness":      {"label": "Re-run readiness evaluation",           "risk": "low"},
    "rerun_rules":          {"label": "Re-run execution rules evaluation",     "risk": "low"},
    "approve_execution":    {"label": "Approve execution",                     "risk": "low"},
    "reject_execution":     {"label": "Reject execution",                      "risk": "medium"},
    "inspect_logs":         {"label": "Inspect logs",                          "risk": "low"},
    "inspect_worktree":     {"label": "Inspect worktree",                      "risk": "low"},
    "open_pr":              {"label": "Open the PR",                           "risk": "low"},
    "reset_to_planning":    {"label": "Reset ticket to planning",              "risk": "destructive"},
    "reset_to_coding":      {"label": "Reset ticket to coding",                "risk": "destructive"},
    "recreate_worktree":    {"label": "Recreate worktree",                     "risk": "high"},
    "recreate_branch":      {"label": "Recreate branch",                       "risk": "high"},
    "sync_ticket_state":    {"label": "Sync ticket state with PR",             "risk": "medium"},
    "archive_ticket":       {"label": "Archive ticket",                        "risk": "destructive"},
    "manual_investigation": {"label": "Manual investigation required",         "risk": "medium"},
}


def _make_action(action_key: str, reason: str) -> dict[str, str]:
    spec = RECOMMENDED_ACTION_CATALOG[action_key]
    return {
        "action_key": action_key,
        "label": spec["label"],
        "risk": spec["risk"],
        "reason": reason,
    }


def _dedupe_actions(actions: list[dict]) -> list[dict]:
    """Preserve insertion order; drop duplicates by ``action_key``."""
    seen: set[str] = set()
    out: list[dict] = []
    for action in actions:
        key = action.get("action_key")
        if key in seen:
            continue
        seen.add(key)
        out.append(action)
    return out


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return runtime_db._now_iso()


def _safe_git(args: list[str], cwd: Path, timeout_s: float) -> subprocess.CompletedProcess | None:
    """Run a git command with a bounded timeout. Returns None on any failure."""
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd),
            timeout=timeout_s,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _parse_iso_to_epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        import datetime
        # Accept the "Z" suffix used by _now_iso.
        text = value.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(text).timestamp()
    except (ValueError, TypeError):
        return None


def _resolve_run_dir(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
) -> Path:
    """Best-effort run-dir resolution mirroring ``resolve_ticket_run_dir`` semantics.

    We avoid importing the Control API service module to keep this file as
    standalone as the rest of ``tools/agent_runner``.
    """
    if worktrees_dir is not None:
        candidate = worktrees_dir / ticket_id / "runs" / ticket_id
        if (candidate / "state.json").exists():
            return candidate
    return project_root / "runs" / ticket_id


def _ticket_exists_on_filesystem(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
) -> bool:
    run_dir = _resolve_run_dir(project_root, ticket_id, worktrees_dir)
    if (run_dir / "state.json").exists():
        return True
    # Also accept presence of ticket.md alone.
    if (run_dir / "ticket.md").exists():
        return True
    return False


# ── Per-check helpers ────────────────────────────────────────────────────────

def _check_ticket_existence(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
    runtime_row: dict | None,
) -> dict:
    fs_present = _ticket_exists_on_filesystem(project_root, ticket_id, worktrees_dir)
    db_present = runtime_row is not None
    if fs_present or db_present:
        details = {"in_filesystem": fs_present, "in_database": db_present}
        return {
            "key": "ticket_existence",
            "status": "passed",
            "message": "Ticket exists in filesystem or runtime DB.",
            "details": details,
        }
    return {
        "key": "ticket_existence",
        "status": "failed",
        "message": f"Ticket {ticket_id} not found in filesystem or runtime DB.",
        "details": {"in_filesystem": False, "in_database": False},
    }


def _check_runtime(db_path, ticket_id: str, runtime_row: dict | None) -> dict:
    if runtime_row is None:
        return {
            "key": "runtime",
            "status": "unknown",
            "message": "No runtime row for ticket.",
            "details": {},
        }
    worker_row: dict | None = None
    try:
        for worker in runtime_db.list_workers(db_path) or []:
            if worker.get("ticket_id") == ticket_id:
                worker_row = worker
                break
    except Exception:
        worker_row = None

    details: dict[str, Any] = {
        "state": runtime_row.get("state"),
        "last_transition": runtime_row.get("last_transition"),
        "last_error": runtime_row.get("last_error"),
        "pr_number": runtime_row.get("pr_number"),
        "pr_state": runtime_row.get("pr_state"),
        "worktree_path": runtime_row.get("worktree_path"),
        "daemon_archived": bool(runtime_row.get("daemon_archived")),
    }
    if worker_row is not None:
        details["reservation"] = {
            "pid": worker_row.get("pid"),
            "status": worker_row.get("status"),
            "heartbeat_at": worker_row.get("heartbeat_at"),
        }
    state = runtime_row.get("state") or "unknown"
    return {
        "key": "runtime",
        "status": "passed",
        "message": f"Runtime state is {state!r}.",
        "details": details,
    }


def _check_intelligence(db_path, ticket_id: str) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    try:
        row = runtime_db.get_ticket_intelligence(db_path, ticket_id)
    except Exception:
        row = None
    if row is None:
        actions.append(_make_action(
            "rerun_intelligence",
            "Ticket Intelligence analysis is missing.",
        ))
        return (
            {
                "key": "intelligence",
                "status": "failed",
                "message": "No intelligence analysis recorded for ticket.",
                "details": {"analysis_status": None},
            },
            actions,
        )
    analysis_status = row.get("analysis_status") or "not_started"
    details = {
        "analysis_status": analysis_status,
        "updated_at": row.get("updated_at"),
    }
    if analysis_status in {"failed", "not_started"}:
        actions.append(_make_action(
            "rerun_intelligence",
            f"Intelligence analysis status is {analysis_status!r}.",
        ))
        return (
            {
                "key": "intelligence",
                "status": "failed",
                "message": f"Intelligence analysis status is {analysis_status!r}.",
                "details": details,
            },
            actions,
        )
    if analysis_status in {"queued", "running"}:
        # Check staleness.
        epoch = _parse_iso_to_epoch(row.get("updated_at"))
        if epoch is not None:
            import time
            age = max(time.time() - epoch, 0)
            if age > _STALE_INTELLIGENCE_SECONDS:
                actions.append(_make_action(
                    "inspect_logs",
                    f"Intelligence analysis has been {analysis_status!r} for "
                    f"{int(age)}s (threshold {_STALE_INTELLIGENCE_SECONDS}s).",
                ))
                return (
                    {
                        "key": "intelligence",
                        "status": "failed",
                        "message": (
                            f"Intelligence analysis stuck in {analysis_status!r} "
                            f"for {int(age)}s."
                        ),
                        "details": details,
                    },
                    actions,
                )
        return (
            {
                "key": "intelligence",
                "status": "passed",
                "message": f"Intelligence analysis is {analysis_status!r}.",
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "intelligence",
            "status": "passed",
            "message": f"Intelligence analysis is {analysis_status!r}.",
            "details": details,
        },
        actions,
    )


def _check_readiness(db_path, ticket_id: str) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    try:
        row = runtime_db.get_ticket_readiness(db_path, ticket_id)
    except Exception:
        row = None
    if row is None:
        actions.append(_make_action(
            "rerun_readiness",
            "Readiness evaluation is missing.",
        ))
        return (
            {
                "key": "readiness",
                "status": "failed",
                "message": "No readiness evaluation recorded for ticket.",
                "details": {"readiness_status": None},
            },
            actions,
        )
    status = row.get("readiness_status") or "not_started"
    blocking = list(row.get("blocking_reasons_json") or [])
    warnings = list(row.get("warnings_json") or [])
    details = {
        "readiness_status": status,
        "ready_candidate": bool(row.get("ready_candidate")),
        "blocking_reasons": blocking,
        "warnings": warnings,
    }
    if status == "failed":
        actions.append(_make_action(
            "rerun_readiness",
            "Readiness evaluation failed.",
        ))
        return (
            {
                "key": "readiness",
                "status": "failed",
                "message": "Readiness evaluation failed.",
                "details": details,
            },
            actions,
        )
    if status == "blocked":
        msg = "Readiness is blocked."
        if blocking:
            msg = f"Readiness is blocked: {blocking[0]}"
        return (
            {
                "key": "readiness",
                "status": "failed",
                "message": msg,
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "readiness",
            "status": "passed",
            "message": f"Readiness status is {status!r}.",
            "details": details,
        },
        actions,
    )


def _check_approval(db_path, ticket_id: str) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    try:
        eligibility = ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)
    except Exception:
        eligibility = "not_started"
    try:
        latest = runtime_db.get_latest_ticket_approval(db_path, ticket_id, "execution")
    except Exception:
        latest = None
    details: dict[str, Any] = {
        "execution_eligibility": eligibility,
        "latest_approval_status": (latest or {}).get("approval_status"),
        "approved_by": (latest or {}).get("approved_by"),
        "approval_comment": (latest or {}).get("approval_comment"),
        "approved_at": (latest or {}).get("approved_at"),
    }
    if eligibility == "ready_candidate":
        actions.append(_make_action(
            "approve_execution",
            "Ticket passed readiness but execution approval is missing.",
        ))
        actions.append(_make_action(
            "reject_execution",
            "Ticket passed readiness but execution approval is missing.",
        ))
        return (
            {
                "key": "approval",
                "status": "failed",
                "message": "Execution approval is missing.",
                "details": details,
            },
            actions,
        )
    if eligibility == "blocked":
        msg = "Execution approval rejected."
        if latest and latest.get("approval_comment"):
            msg = f"Execution approval rejected: {latest['approval_comment']}"
        return (
            {
                "key": "approval",
                "status": "failed",
                "message": msg,
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "approval",
            "status": "passed",
            "message": f"Execution eligibility is {eligibility!r}.",
            "details": details,
        },
        actions,
    )


def _check_rules(db_path, ticket_id: str) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    try:
        row = runtime_db.get_ticket_rule_evaluation(db_path, ticket_id)
    except Exception:
        row = None
    if row is None:
        actions.append(_make_action(
            "rerun_rules",
            "No execution rules evaluation found.",
        ))
        return (
            {
                "key": "rules",
                "status": "failed",
                "message": "No execution rules evaluation recorded for ticket.",
                "details": {"eligibility_status": None},
            },
            actions,
        )
    status = row.get("eligibility_status") or "unknown"
    failed_rules = list(row.get("failed_rules_json") or [])
    details = {
        "eligibility_status": status,
        "failed_rules": failed_rules,
    }
    if status == "blocked":
        first = ""
        if failed_rules and isinstance(failed_rules[0], dict):
            first = failed_rules[0].get("rule_key") or ""
        msg = "Execution rules blocked the ticket."
        if first:
            msg = f"Execution rules blocked the ticket ({first})."
        return (
            {
                "key": "rules",
                "status": "failed",
                "message": msg,
                "details": details,
            },
            actions,
        )
    if status in {"failed", "stale"}:
        actions.append(_make_action(
            "rerun_rules",
            f"Execution rules evaluation is {status!r}.",
        ))
        return (
            {
                "key": "rules",
                "status": "failed",
                "message": f"Execution rules evaluation is {status!r}.",
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "rules",
            "status": "passed",
            "message": f"Execution rules eligibility is {status!r}.",
            "details": details,
        },
        actions,
    )


def _check_worktree(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
    runtime_row: dict | None,
    timeout_s: float,
) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    expected_path: Path | None = None
    if runtime_row and runtime_row.get("worktree_path"):
        try:
            expected_path = Path(runtime_row["worktree_path"])
        except (TypeError, ValueError):
            expected_path = None
    if expected_path is None and worktrees_dir is not None:
        expected_path = worktrees_dir / ticket_id

    if expected_path is None:
        return (
            {
                "key": "worktree",
                "status": "unknown",
                "message": "Worktree location unknown.",
                "details": {"expected_path": None},
            },
            actions,
        )

    details: dict[str, Any] = {"expected_path": str(expected_path)}
    if not expected_path.exists():
        details["worktree_status"] = "missing"
        if runtime_row and runtime_row.get("state") and runtime_row["state"] not in _DONE_STATES:
            actions.append(_make_action(
                "recreate_worktree",
                f"Worktree missing at {expected_path}.",
            ))
            actions.append(_make_action(
                "reset_to_planning",
                "Worktree missing while ticket is mid-flow.",
            ))
        return (
            {
                "key": "worktree",
                "status": "failed",
                "message": f"Worktree missing at {expected_path}.",
                "details": details,
            },
            actions,
        )

    # Worktree exists — check for dirty state via git status --porcelain.
    git_result = _safe_git(["status", "--porcelain"], expected_path, timeout_s)
    if git_result is None or git_result.returncode != 0:
        details["worktree_status"] = "unknown"
        return (
            {
                "key": "worktree",
                "status": "unknown",
                "message": "Could not determine worktree cleanliness.",
                "details": details,
            },
            actions,
        )
    dirty = bool(git_result.stdout.strip())
    details["worktree_status"] = "dirty" if dirty else "clean"
    if dirty:
        actions.append(_make_action(
            "inspect_worktree",
            "Worktree has uncommitted changes.",
        ))
        return (
            {
                "key": "worktree",
                "status": "failed",
                "message": f"Worktree at {expected_path} is dirty.",
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "worktree",
            "status": "passed",
            "message": f"Worktree at {expected_path} is clean.",
            "details": details,
        },
        actions,
    )


def _check_branch(
    project_root: Path,
    runtime_row: dict | None,
    timeout_s: float,
) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    branch = (runtime_row or {}).get("branch")
    if not branch:
        return (
            {
                "key": "branch",
                "status": "unknown",
                "message": "No branch recorded for ticket.",
                "details": {"branch": None},
            },
            actions,
        )
    details: dict[str, Any] = {"branch": branch}
    result = _safe_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        project_root,
        timeout_s,
    )
    if result is None:
        details["branch_status"] = "unknown"
        return (
            {
                "key": "branch",
                "status": "unknown",
                "message": f"Could not verify branch {branch!r}.",
                "details": details,
            },
            actions,
        )
    if result.returncode == 0:
        details["branch_status"] = "exists"
        return (
            {
                "key": "branch",
                "status": "passed",
                "message": f"Branch {branch!r} exists.",
                "details": details,
            },
            actions,
        )
    details["branch_status"] = "missing"
    state = (runtime_row or {}).get("state")
    if state and state not in _DONE_STATES:
        actions.append(_make_action(
            "recreate_branch",
            f"Branch {branch!r} is missing while ticket is active.",
        ))
        return (
            {
                "key": "branch",
                "status": "failed",
                "message": f"Branch {branch!r} not found.",
                "details": details,
            },
            actions,
        )
    # For DONE/MERGED tickets, a missing branch is expected (branch deleted
    # after merge). Surface as passed but record the absence in details.
    return (
        {
            "key": "branch",
            "status": "passed",
            "message": f"Branch {branch!r} not found (expected for completed ticket).",
            "details": details,
        },
        actions,
    )


def _check_pr(runtime_row: dict | None) -> tuple[dict, list[dict]]:
    actions: list[dict] = []
    if runtime_row is None:
        return (
            {
                "key": "pr",
                "status": "unknown",
                "message": "No runtime data; PR status unknown.",
                "details": {"pr_status": "unknown"},
            },
            actions,
        )
    pr_number = runtime_row.get("pr_number")
    pr_state = (runtime_row.get("pr_state") or "").lower()
    if not pr_number:
        return (
            {
                "key": "pr",
                "status": "passed",
                "message": "No PR has been opened yet.",
                "details": {"pr_status": "no_pr"},
            },
            actions,
        )
    details: dict[str, Any] = {
        "pr_status": pr_state or "unknown",
        "pr_number": pr_number,
    }
    if pr_state == "open":
        actions.append(_make_action("open_pr", f"PR #{pr_number} is open."))
        return (
            {
                "key": "pr",
                "status": "passed",
                "message": f"PR #{pr_number} is open.",
                "details": details,
            },
            actions,
        )
    if pr_state == "merged":
        ticket_state = (runtime_row.get("state") or "").upper()
        if ticket_state not in _DONE_STATES:
            actions.append(_make_action(
                "sync_ticket_state",
                f"PR #{pr_number} is merged but ticket state is {ticket_state or 'unset'!r}.",
            ))
            return (
                {
                    "key": "pr",
                    "status": "failed",
                    "message": (
                        f"PR #{pr_number} merged but ticket state is "
                        f"{ticket_state or 'unset'!r}."
                    ),
                    "details": details,
                },
                actions,
            )
        return (
            {
                "key": "pr",
                "status": "passed",
                "message": f"PR #{pr_number} is merged.",
                "details": details,
            },
            actions,
        )
    if pr_state in {"closed", "closed_unmerged"}:
        actions.append(_make_action(
            "reset_to_planning",
            f"PR #{pr_number} was closed without merging.",
        ))
        actions.append(_make_action(
            "archive_ticket",
            f"PR #{pr_number} was closed without merging; archiving may be appropriate.",
        ))
        return (
            {
                "key": "pr",
                "status": "failed",
                "message": f"PR #{pr_number} closed without merging.",
                "details": details,
            },
            actions,
        )
    return (
        {
            "key": "pr",
            "status": "unknown",
            "message": f"PR #{pr_number} is in unrecognized state {pr_state!r}.",
            "details": details,
        },
        actions,
    )


def _check_logs(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
) -> dict:
    run_dir = _resolve_run_dir(project_root, ticket_id, worktrees_dir)
    if not run_dir.exists():
        return {
            "key": "logs",
            "status": "unknown",
            "message": "Run directory does not exist.",
            "details": {"run_dir": str(run_dir)},
        }
    log_file = run_dir / "runtime.log"
    details: dict[str, Any] = {
        "run_dir": str(run_dir),
        "plan_present": (run_dir / "plan.md").exists(),
        "review_present": (run_dir / "review.md").exists(),
        "tests_present": (run_dir / "tests.md").exists(),
    }
    if not log_file.exists():
        details["latest_log_path"] = None
        return {
            "key": "logs",
            "status": "unknown",
            "message": "No runtime.log found.",
            "details": details,
        }
    try:
        stat = log_file.stat()
    except OSError:
        details["latest_log_path"] = str(log_file)
        return {
            "key": "logs",
            "status": "unknown",
            "message": "Could not stat runtime.log.",
            "details": details,
        }
    details["latest_log_path"] = str(log_file)
    details["latest_log_mtime"] = stat.st_mtime
    details["latest_log_size"] = stat.st_size
    if stat.st_size <= _LOG_MAX_BYTES:
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
            tail = text.splitlines()[-_LOG_TAIL_LINES:]
            details["latest_log_tail"] = "\n".join(tail)
        except OSError:
            details["latest_log_tail"] = None
    else:
        details["latest_log_tail"] = None
    return {
        "key": "logs",
        "status": "passed",
        "message": f"runtime.log found ({stat.st_size} bytes).",
        "details": details,
    }


def _check_context_freshness(
    db_path,
    project_root: Path,
    ticket_id: str,
    timeout_s: float,
) -> dict:
    try:
        readiness = runtime_db.get_ticket_readiness(db_path, ticket_id)
    except Exception:
        readiness = None
    recorded = (readiness or {}).get("main_sha_when_evaluated")
    if not recorded:
        return {
            "key": "context_freshness",
            "status": "unknown",
            "message": "No recorded main SHA from prior evaluation.",
            "details": {"recorded_main_sha": None, "current_main_sha": None},
        }
    # Try origin/main first then main.
    current = None
    for ref in ("origin/main", "main"):
        result = _safe_git(["rev-parse", ref], project_root, timeout_s)
        if result is not None and result.returncode == 0 and result.stdout.strip():
            current = result.stdout.strip()
            break
    if current is None:
        return {
            "key": "context_freshness",
            "status": "unknown",
            "message": "Could not resolve current main SHA.",
            "details": {"recorded_main_sha": recorded, "current_main_sha": None},
        }
    if current.startswith(recorded) or recorded.startswith(current):
        return {
            "key": "context_freshness",
            "status": "passed",
            "message": "Context is fresh.",
            "details": {
                "recorded_main_sha": recorded,
                "current_main_sha": current,
                "freshness": "fresh",
            },
        }
    return {
        "key": "context_freshness",
        "status": "passed",
        "message": "Context may be stale (advisory only).",
        "details": {
            "recorded_main_sha": recorded,
            "current_main_sha": current,
            "freshness": "stale",
        },
    }


# ── Summary + severity derivation ────────────────────────────────────────────

# Declared priority order — first failed check wins for severity/summary.
_CHECK_PRIORITY = (
    "ticket_existence",
    "runtime",
    "readiness",
    "approval",
    "rules",
    "worktree",
    "branch",
    "pr",
    "intelligence",
    "logs",
    "context_freshness",
)


def _derive_summary_and_severity(checks: list[dict], runtime_row: dict | None) -> dict:
    """Return ``{is_stuck, severity, summary, current_state, last_known_step, last_error}``."""
    by_key = {c["key"]: c for c in checks}
    severity = "info"
    summary = "Ticket has no detected blockers."
    is_stuck = False
    first_failed_key: str | None = None
    for key in _CHECK_PRIORITY:
        check = by_key.get(key)
        if check is None:
            continue
        if check.get("status") == "failed":
            first_failed_key = key
            break

    if first_failed_key is not None:
        is_stuck = True
        summary = by_key[first_failed_key].get("message") or "Ticket is stuck."
        if first_failed_key in {"ticket_existence"}:
            severity = "error"
        elif first_failed_key in {"runtime"}:
            severity = "error"
        else:
            severity = "warning"

    current_state = (runtime_row or {}).get("state")
    last_error = (runtime_row or {}).get("last_error")
    last_known_step = (runtime_row or {}).get("last_transition")
    return {
        "is_stuck": is_stuck,
        "severity": severity,
        "summary": summary,
        "current_state": current_state,
        "last_known_step": last_known_step,
        "last_error": last_error,
    }


# ── Public assembly ──────────────────────────────────────────────────────────

def build_diagnostic(
    ticket_id: str,
    checks: list[dict],
    actions: list[dict],
    runtime_row: dict | None,
    generated_at: str | None = None,
) -> dict:
    """Assemble the final diagnostic dict from pre-computed pieces.

    Pure helper exposed so tests can drive the assembly without disk/Git access.
    """
    derived = _derive_summary_and_severity(checks, runtime_row)
    return {
        "ticket_id": ticket_id,
        "diagnostic_status": "completed",
        "is_stuck": derived["is_stuck"],
        "severity": derived["severity"],
        "summary": derived["summary"],
        "current_state": derived["current_state"],
        "last_known_step": derived["last_known_step"],
        "last_error": derived["last_error"],
        "checks": checks,
        "recommended_actions": _dedupe_actions(actions),
        "generated_at": generated_at or _now_iso(),
    }


def _persist_result(db_path, ticket_id: str, project_id: str | None, result: dict) -> None:
    try:
        runtime_db.upsert_ticket_diagnostics(
            db_path,
            ticket_id,
            project_id=project_id,
            diagnostic_status=result["diagnostic_status"],
            is_stuck=1 if result["is_stuck"] else 0,
            severity=result["severity"],
            summary=result["summary"],
            current_state=result["current_state"],
            last_known_step=result["last_known_step"],
            last_error=result["last_error"],
            checks_json=result["checks"],
            recommended_actions_json=result["recommended_actions"],
            generated_at=result["generated_at"],
        )
    except Exception:
        # Persisting is best-effort: a diagnostic that cannot be stored should
        # still be returned to the caller (read-only behaviour).
        pass


def diagnose_ticket(
    db_path,
    project_root: Path,
    ticket_id: str,
    *,
    worktrees_dir: Path | None = None,
    project_id: str | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    persist: bool = True,
) -> dict:
    """Run the full diagnostic pipeline. Deterministic, bounded, never raises."""
    try:
        runtime_row = runtime_db.get_ticket_runtime(db_path, ticket_id)
    except Exception:
        runtime_row = None

    existence = _check_ticket_existence(
        project_root, ticket_id, worktrees_dir, runtime_row,
    )

    # If the ticket does not exist at all, short-circuit.
    if existence["status"] == "failed":
        actions = [_make_action(
            "manual_investigation",
            f"Ticket {ticket_id} not found in filesystem or DB.",
        )]
        result = build_diagnostic(ticket_id, [existence], actions, runtime_row)
        # Overwrite severity to error for missing-ticket cases.
        result["severity"] = "error"
        result["is_stuck"] = True
        if persist:
            _persist_result(db_path, ticket_id, project_id, result)
        return result

    checks: list[dict] = [existence]
    actions: list[dict] = []

    runtime_check = _check_runtime(db_path, ticket_id, runtime_row)
    checks.append(runtime_check)

    readiness_check, readiness_actions = _check_readiness(db_path, ticket_id)
    checks.append(readiness_check)
    actions.extend(readiness_actions)

    approval_check, approval_actions = _check_approval(db_path, ticket_id)
    checks.append(approval_check)
    actions.extend(approval_actions)

    rules_check, rules_actions = _check_rules(db_path, ticket_id)
    checks.append(rules_check)
    actions.extend(rules_actions)

    worktree_check, worktree_actions = _check_worktree(
        project_root, ticket_id, worktrees_dir, runtime_row, timeout_s,
    )
    checks.append(worktree_check)
    actions.extend(worktree_actions)

    branch_check, branch_actions = _check_branch(
        project_root, runtime_row, timeout_s,
    )
    checks.append(branch_check)
    actions.extend(branch_actions)

    pr_check, pr_actions = _check_pr(runtime_row)
    checks.append(pr_check)
    actions.extend(pr_actions)

    intelligence_check, intelligence_actions = _check_intelligence(db_path, ticket_id)
    checks.append(intelligence_check)
    actions.extend(intelligence_actions)

    logs_check = _check_logs(project_root, ticket_id, worktrees_dir)
    checks.append(logs_check)

    freshness_check = _check_context_freshness(
        db_path, project_root, ticket_id, timeout_s,
    )
    checks.append(freshness_check)

    result = build_diagnostic(ticket_id, checks, actions, runtime_row)
    if persist:
        _persist_result(db_path, ticket_id, project_id, result)
    return result


__all__ = [
    "diagnose_ticket",
    "build_diagnostic",
    "RECOMMENDED_ACTION_CATALOG",
]
