"""Board projection — maps runs/* state files + gh issue list to 7 kanban columns."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from ..models.schemas import BoardColumn, BoardItem, BoardResponse

_TICKET_RE = re.compile(r"^T\d{3,}$")
_HUMAN_GATE_STATES = frozenset({"PLAN_REVIEW_NEEDED", "TEST_COMPLETE"})
_ISSUE_INDEX_FILENAME = ".issue-intake.json"
_WORKERS_REGISTRY_FILENAME = "workers.json"

_COLUMN_ORDER = [
    ("backlog", "Backlog"),
    ("queued", "Queued"),
    ("running", "Running"),
    ("waiting_human", "Waiting human"),
    ("blocked", "Blocked"),
    ("pr_ready", "PR ready"),
    ("done", "Done"),
]


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _lock_held(ticket_dir: Path) -> bool:
    lock = ticket_dir / "daemon.lock"
    if not lock.exists():
        return False
    data = _load_json(lock)
    pid = data.get("pid")
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _load_workers_registry(runs_dir: Path) -> dict[str, dict]:
    path = runs_dir / _WORKERS_REGISTRY_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_issue_index(runs_dir: Path) -> dict[str, str]:
    path = runs_dir / _ISSUE_INDEX_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _fetch_ai_ready_issues(repo: str | None) -> list[dict]:
    cmd = ["gh", "issue", "list", "--label", "ai-ready", "--json", "number,title", "--state", "open"]
    if repo:
        cmd += ["--repo", repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_board(project_root: Path, repo: str | None = None) -> BoardResponse:
    runs_dir = project_root / "runs"
    columns: dict[str, list[BoardItem]] = {col_id: [] for col_id, _ in _COLUMN_ORDER}
    workers = _load_workers_registry(runs_dir) if runs_dir.exists() else {}

    # Collect tickets from runs/ and any active worktrees
    ticket_dirs: dict[str, Path] = {}
    if runs_dir.exists():
        for ticket_dir in sorted(runs_dir.iterdir()):
            if _TICKET_RE.match(ticket_dir.name):
                ticket_dirs[ticket_dir.name] = ticket_dir

    # For workers with a worktree, prefer the worktree's run_dir for state
    for ticket_id, worker in workers.items():
        wt_path = worker.get("worktree_path")
        if wt_path:
            wt_run_dir = Path(wt_path) / "runs" / ticket_id
            if wt_run_dir.exists():
                ticket_dirs[ticket_id] = wt_run_dir

    for ticket_id, ticket_dir in sorted(ticket_dirs.items()):
        state_data = _load_json(ticket_dir / "state.json")
        if not state_data:
            continue
        state = state_data.get("state", "")
        worker_info = workers.get(ticket_id, {})
        item = BoardItem(
            ticket_id=ticket_id,
            issue_number=state_data.get("issue_number"),
            state=state,
            branch=state_data.get("branch"),
            worker_pid=worker_info.get("pid"),
            worker_cwd=worker_info.get("worktree_path"),
        )
        # Priority: first match wins
        if state_data.get("daemon_archived") or state_data.get("issue_closed"):
            columns["done"].append(item)
        elif state == "TEST_COMPLETE" and state_data.get("pr_number"):
            columns["pr_ready"].append(item)
        elif state in _HUMAN_GATE_STATES:
            columns["waiting_human"].append(item)
        elif _load_json(ticket_dir / "retry-state.json").get("stopped"):
            columns["blocked"].append(item)
        elif ticket_id in workers or _lock_held(ticket_dir):
            columns["running"].append(item)
        else:
            columns["queued"].append(item)

    # Backlog: ai-ready issues not yet ingested
    issue_index = _load_issue_index(runs_dir) if runs_dir.exists() else {}
    ingested = set(issue_index.keys())
    for issue in _fetch_ai_ready_issues(repo):
        if str(issue["number"]) not in ingested:
            columns["backlog"].append(BoardItem(
                issue_number=issue["number"],
                title=issue.get("title"),
            ))

    return BoardResponse(
        columns=[
            BoardColumn(id=col_id, label=label, items=columns[col_id])
            for col_id, label in _COLUMN_ORDER
        ]
    )
