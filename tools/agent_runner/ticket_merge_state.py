"""Resolve whether a ticket's PR has been merged into ``main``.

Single public helper used by the Readiness Evaluator so the evaluator never
shells out to ``git`` directly. Resolution order — return on the first
definitive answer; only fall through on ``unknown``:

    1. Runtime DB     — ticket_runtime / PR rows with a recorded merge state.
    2. GitHub metadata — ``gh pr view`` for the ticket's PR if discoverable.
    3. Git fallback   — ``git log --grep "T<id>" main`` on the project's repo.

The return value is a small ``MergeCheckResult`` dataclass carrying the
status (``merged | not_merged | unknown``), the source used to decide, and a
short human-readable reason.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


_GIT_TIMEOUT = 10
_GH_TIMEOUT = 10


@dataclass
class MergeCheckResult:
    status: str  # "merged" | "not_merged" | "unknown"
    source: str  # "runtime_db" | "github_metadata" | "git_fallback" | "unknown"
    reason: str = ""


def _normalize_ticket_id(ticket_id: str) -> str:
    return ticket_id.strip()


# ── Layer 1: runtime DB ──────────────────────────────────────────────────────

def _runtime_db_check(ticket_id: str) -> MergeCheckResult | None:
    """Inspect the runtime DB. Return None when the layer cannot decide."""
    try:
        db_path = runtime_db.get_db_path()
    except Exception:
        return None
    if db_path is None:
        return None

    try:
        row = runtime_db.get_ticket_runtime(db_path, ticket_id)
    except Exception:
        return None

    if not row:
        return None

    pr_state = (row.get("pr_state") or "").strip().lower()
    state = (row.get("state") or "").strip().lower()

    if pr_state in {"merged"} or state in {"merged"}:
        return MergeCheckResult(
            status="merged",
            source="runtime_db",
            reason=f"runtime_db pr_state={row.get('pr_state')!r} state={row.get('state')!r}",
        )

    if pr_state in {"closed"}:
        # Closed but not merged.
        return MergeCheckResult(
            status="not_merged",
            source="runtime_db",
            reason="runtime_db PR is closed without merge",
        )

    return None


# ── Layer 2: GitHub metadata via ``gh`` ──────────────────────────────────────

def _resolve_pr_number_from_db(ticket_id: str) -> int | None:
    """Best-effort PR number lookup from ticket_runtime (used by ``gh pr view``)."""
    try:
        db_path = runtime_db.get_db_path()
    except Exception:
        return None
    if db_path is None:
        return None
    try:
        row = runtime_db.get_ticket_runtime(db_path, ticket_id)
    except Exception:
        return None
    if not row:
        return None
    pr = row.get("pr_number")
    if pr is None:
        return None
    try:
        return int(pr)
    except (TypeError, ValueError):
        return None


def _gh_pr_view(project_root: Path, pr_number: int) -> dict | None:
    try:
        proc = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state,mergedAt"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _github_metadata_check(project_root: Path, ticket_id: str) -> MergeCheckResult | None:
    pr_number = _resolve_pr_number_from_db(ticket_id)
    if pr_number is None:
        return None

    data = _gh_pr_view(project_root, pr_number)
    if data is None:
        return None

    state = (data.get("state") or "").upper()
    merged_at = data.get("mergedAt")

    if state == "MERGED" or merged_at:
        return MergeCheckResult(
            status="merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=MERGED",
        )
    if state in {"CLOSED"}:
        return MergeCheckResult(
            status="not_merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=CLOSED",
        )
    if state in {"OPEN"}:
        return MergeCheckResult(
            status="not_merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=OPEN",
        )
    return None


# ── Layer 3: git fallback ────────────────────────────────────────────────────

_TICKET_ID_RE = re.compile(r"^T\d+$", re.IGNORECASE)


def _git_log_grep(project_root: Path, ticket_id: str) -> MergeCheckResult | None:
    """Return ``merged`` when a commit reachable from ``main`` mentions the ticket."""
    if not _TICKET_ID_RE.match(ticket_id):
        return None
    try:
        proc = subprocess.run(
            ["git", "log", "main", "--grep", ticket_id, "--oneline"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    if proc.stdout.strip():
        return MergeCheckResult(
            status="merged",
            source="git_fallback",
            reason=f"git log main --grep {ticket_id} found commit(s)",
        )
    return MergeCheckResult(
        status="not_merged",
        source="git_fallback",
        reason=f"git log main --grep {ticket_id} found no commits",
    )


# ── Public entry point ───────────────────────────────────────────────────────

def is_ticket_merged(project_root: Path, ticket_id: str) -> MergeCheckResult:
    """Return whether ``ticket_id`` has been merged into the project's ``main`` branch.

    Tries runtime DB → GitHub metadata → git log, in order. Returns the first
    layer that produces a definitive ``merged`` / ``not_merged`` answer.
    """
    ticket_id = _normalize_ticket_id(ticket_id)

    for resolver in (
        lambda: _runtime_db_check(ticket_id),
        lambda: _github_metadata_check(Path(project_root), ticket_id),
        lambda: _git_log_grep(Path(project_root), ticket_id),
    ):
        try:
            result = resolver()
        except Exception:
            result = None
        if result is not None:
            return result

    return MergeCheckResult(
        status="unknown",
        source="unknown",
        reason="no source could decide merge state",
    )
