"""Resolve whether a ticket's PR has been merged into ``main``.

Single public helper used by the Readiness Evaluator so the evaluator never
shells out to ``git`` directly. Resolution order — return on the first
definitive answer; only fall through on ``unknown``:

    1. Runtime DB     — ``ticket_runtime.pr_state`` when already synced.
    2. GitHub metadata — ``gh pr view`` for the ticket's PR when ``pr_number`` is known.

The return value is a small ``MergeCheckResult`` dataclass carrying the
status (``merged | not_merged | unknown``), the source used to decide, and a
short human-readable reason.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


_GH_TIMEOUT = 10


@dataclass
class MergeCheckResult:
    status: str  # "merged" | "not_merged" | "unknown"
    source: str  # "runtime_db" | "github_metadata" | "unknown"
    reason: str = ""


def _normalize_ticket_id(ticket_id: str) -> str:
    return ticket_id.strip()


def _resolve_db_path(project_id: str | None = None):
    try:
        if project_id:
            return runtime_db.get_db_path(project_id)
        return runtime_db.get_db_path()
    except Exception:
        return None


def _state_json_candidates(
    project_root: Path,
    ticket_id: str,
    project_id: str | None,
) -> list[Path]:
    candidates: list[Path] = []
    runtime_base = os.environ.get("RUNTIME_BASE_ROOT") or os.environ.get(
        "AI_DEV_FACTORY_RUNTIME_ROOT"
    )
    if project_id and runtime_base:
        candidates.append(
            Path(runtime_base).expanduser()
            / project_id
            / "worktrees"
            / ticket_id
            / "runs"
            / ticket_id
            / "state.json"
        )
    candidates.append(project_root / "runs" / ticket_id / "state.json")
    return candidates


def _load_state_json(
    project_root: Path,
    ticket_id: str,
    project_id: str | None,
) -> dict | None:
    for path in _state_json_candidates(project_root, ticket_id, project_id):
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _resolve_pr_number(
    ticket_id: str,
    project_root: Path,
    project_id: str | None,
) -> int | None:
    db_path = _resolve_db_path(project_id)
    if db_path is not None:
        try:
            row = runtime_db.get_ticket_runtime(db_path, ticket_id)
        except Exception:
            row = None
        if row and row.get("pr_number") is not None:
            try:
                return int(row["pr_number"])
            except (TypeError, ValueError):
                pass

    state = _load_state_json(project_root, ticket_id, project_id)
    if state and state.get("pr_number") is not None:
        try:
            return int(state["pr_number"])
        except (TypeError, ValueError):
            pass
    return None


def _ticket_exists(
    ticket_id: str,
    project_root: Path,
    project_id: str | None,
) -> bool:
    db_path = _resolve_db_path(project_id)
    if db_path is not None:
        try:
            if runtime_db.get_ticket_runtime(db_path, ticket_id):
                return True
        except Exception:
            pass
    return _load_state_json(project_root, ticket_id, project_id) is not None


# ── Layer 1: runtime DB ──────────────────────────────────────────────────────

def _runtime_db_check(
    ticket_id: str,
    project_id: str | None,
) -> MergeCheckResult | None:
    """Inspect cached ``pr_state`` in the runtime DB."""
    db_path = _resolve_db_path(project_id)
    if db_path is None:
        return None

    try:
        row = runtime_db.get_ticket_runtime(db_path, ticket_id)
    except Exception:
        return None

    if not row:
        return None

    pr_state = (row.get("pr_state") or "").strip().lower()

    if pr_state == "merged":
        return MergeCheckResult(
            status="merged",
            source="runtime_db",
            reason=f"runtime_db pr_state={row.get('pr_state')!r}",
        )

    if pr_state in {"closed", "open"}:
        label = "open" if pr_state == "open" else "closed without merge"
        return MergeCheckResult(
            status="not_merged",
            source="runtime_db",
            reason=f"runtime_db PR is {label}",
        )

    return None


# ── Layer 2: GitHub metadata via ``gh`` ──────────────────────────────────────

def _gh_pr_view(
    project_root: Path,
    pr_number: int,
    *,
    repo: str | None = None,
) -> dict | None:
    """Fetch PR state via REST (``gh api``), not GraphQL ``gh pr view``."""
    owner_repo = (repo or "").strip()
    if not owner_repo or "/" not in owner_repo:
        try:
            origin = subprocess.run(
                ["git", "-C", str(project_root), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=_GH_TIMEOUT,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        url = (origin.stdout or "").strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if not m:
            return None
        owner_repo = f"{m.group(1)}/{m.group(2)}"
    cmd = ["gh", "api", f"repos/{owner_repo}/pulls/{pr_number}"]
    try:
        proc = subprocess.run(
            cmd,
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
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    # Normalize REST → GraphQL-ish shape expected by _merge_result_from_github_payload.
    merged = bool(data.get("merged"))
    state = "MERGED" if merged else str(data.get("state") or "").upper()
    return {
        "state": state,
        "mergedAt": data.get("merged_at"),
    }


def _merge_result_from_github_payload(
    pr_number: int,
    data: dict,
) -> MergeCheckResult:
    state = (data.get("state") or "").upper()
    merged_at = data.get("mergedAt")

    if state == "MERGED" or merged_at:
        return MergeCheckResult(
            status="merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=MERGED",
        )
    if state == "CLOSED":
        return MergeCheckResult(
            status="not_merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=CLOSED",
        )
    if state == "OPEN":
        return MergeCheckResult(
            status="not_merged",
            source="github_metadata",
            reason=f"gh pr view #{pr_number} state=OPEN",
        )
    return MergeCheckResult(
        status="unknown",
        source="unknown",
        reason=f"gh pr view #{pr_number} returned unrecognized state {state!r}",
    )


def fetch_github_pr_state_label(
    project_root: Path,
    pr_number: int,
    *,
    repo: str | None = None,
) -> str | None:
    """Return ``merged``, ``open``, ``closed``, or ``None`` when gh is unavailable."""
    data = _gh_pr_view(project_root, pr_number, repo=repo)
    if data is None:
        return None
    state = (data.get("state") or "").upper()
    if state == "MERGED" or data.get("mergedAt"):
        return "merged"
    if state == "OPEN":
        return "open"
    if state == "CLOSED":
        return "closed"
    return None


def _github_metadata_check(
    project_root: Path,
    ticket_id: str,
    *,
    project_id: str | None,
    repo: str | None,
) -> MergeCheckResult | None:
    pr_number = _resolve_pr_number(ticket_id, project_root, project_id)
    if pr_number is None:
        return None

    data = _gh_pr_view(project_root, pr_number, repo=repo)
    if data is None:
        return None

    return _merge_result_from_github_payload(pr_number, data)


# ── Public entry point ───────────────────────────────────────────────────────

def is_ticket_merged(
    project_root: Path,
    ticket_id: str,
    *,
    project_id: str | None = None,
    repo: str | None = None,
) -> MergeCheckResult:
    """Return whether ``ticket_id`` has been merged into the project's ``main`` branch.

    Uses cached ``pr_state`` in the runtime DB when available, then queries
    GitHub via ``gh pr view`` when a ``pr_number`` is known. Tickets with no
    recorded PR are treated as ``not_merged``.
    """
    ticket_id = _normalize_ticket_id(ticket_id)
    project_root = Path(project_root)

    cached = _runtime_db_check(ticket_id, project_id)
    if cached is not None:
        return cached

    github = _github_metadata_check(
        project_root,
        ticket_id,
        project_id=project_id,
        repo=repo,
    )
    if github is not None:
        return github

    pr_number = _resolve_pr_number(ticket_id, project_root, project_id)
    if pr_number is not None:
        return MergeCheckResult(
            status="unknown",
            source="unknown",
            reason=f"gh pr view #{pr_number} unavailable",
        )

    if _ticket_exists(ticket_id, project_root, project_id):
        return MergeCheckResult(
            status="not_merged",
            source="github_metadata",
            reason=f"{ticket_id} has no PR recorded",
        )

    return MergeCheckResult(
        status="unknown",
        source="unknown",
        reason=f"no runtime record or PR found for {ticket_id}",
    )
