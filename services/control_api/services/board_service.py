"""Board projection — maps runs/* state files + gh issue list to 7 kanban columns."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

from ..models.schemas import BoardColumn, BoardItem, BoardResponse
from .runtime_resolver import resolve_runs_dir, resolve_state_dir

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


def _load_runtime_db(project_root: Path):
    """Load the runtime_db module if the SQLite DB exists. Returns (module, db_path) or (None, None)."""
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        db_path = Path(runtime_root) / ".runtime" / "ai-dev-factory.sqlite"
    else:
        db_path = project_root / ".runtime" / "ai-dev-factory.sqlite"
    if not db_path.exists():
        return None, None
    try:
        _tools = Path(__file__).resolve().parent.parent.parent.parent / "tools" / "agent_runner"
        spec = importlib.util.spec_from_file_location("_rdb_board", _tools / "runtime_db.py")
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod, db_path
    except Exception:
        return None, None


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


def get_board(project_root: Path, repo: str | None = None, worktrees_dir: Path | None = None) -> BoardResponse:
    runs_dir = resolve_runs_dir(project_root)
    state_dir = resolve_state_dir(project_root)
    columns: dict[str, list[BoardItem]] = {col_id: [] for col_id, _ in _COLUMN_ORDER}

    rdb, db_path = _load_runtime_db(project_root)

    if rdb and db_path:
        workers = {
            w["ticket_id"]: {"pid": w["pid"], "branch": w["branch"], "worktree_path": w["worktree_path"]}
            for w in rdb.list_workers(db_path)
        }
    else:
        workers = _load_workers_registry(state_dir) if state_dir.exists() else {}

    # Collect tickets from runs/ (main repo)
    ticket_dirs: dict[str, Path] = {}
    if runs_dir.exists():
        for ticket_dir in sorted(runs_dir.iterdir()):
            if _TICKET_RE.match(ticket_dir.name):
                ticket_dirs[ticket_dir.name] = ticket_dir

    # Active workers with a worktree override the main runs/ entry
    for ticket_id, worker in workers.items():
        wt_path = worker.get("worktree_path")
        if wt_path:
            wt_run_dir = Path(wt_path) / "runs" / ticket_id
            if wt_run_dir.exists():
                ticket_dirs[ticket_id] = wt_run_dir

    # Scan worktrees_dir for tickets that have a worktree but are not in workers.json
    if worktrees_dir and worktrees_dir.exists():
        for wt_dir in sorted(worktrees_dir.iterdir()):
            if not wt_dir.is_dir() or not _TICKET_RE.match(wt_dir.name):
                continue
            ticket_id = wt_dir.name
            if ticket_id in workers:
                continue  # already handled via workers entry above
            wt_run_dir = wt_dir / "runs" / ticket_id
            if wt_run_dir.exists():
                ticket_dirs[ticket_id] = wt_run_dir

    # Load ticket_runtime from SQLite — primary source for kanban state
    sqlite_ticket_states: dict[str, dict] = {}
    if rdb and db_path:
        try:
            for row in rdb.list_ticket_runtime(db_path):
                sqlite_ticket_states[row["ticket_id"]] = row
        except Exception:
            pass  # degraded: fall back to state.json only

    # Union of filesystem-discovered tickets and SQLite-known tickets
    all_ticket_ids = sorted(set(ticket_dirs.keys()) | set(sqlite_ticket_states.keys()))

    for ticket_id in all_ticket_ids:
        ticket_dir = ticket_dirs.get(ticket_id)
        sqlite_row = sqlite_ticket_states.get(ticket_id)

        if sqlite_row:
            state = sqlite_row.get("state") or ""
            issue_number = sqlite_row.get("issue_number")
            branch = sqlite_row.get("branch")
            daemon_archived = bool(sqlite_row.get("daemon_archived"))
            pr_number = sqlite_row.get("pr_number")
            state_data = _load_json(ticket_dir / "state.json") if ticket_dir else {}
            issue_closed = state_data.get("issue_closed", False)
            retry_stopped = (
                _load_json(ticket_dir / "retry-state.json").get("stopped", False)
                if ticket_dir else False
            )
        else:
            if not ticket_dir:
                continue
            state_data = _load_json(ticket_dir / "state.json")
            if not state_data:
                continue
            state = state_data.get("state", "")
            issue_number = state_data.get("issue_number")
            branch = state_data.get("branch")
            daemon_archived = bool(state_data.get("daemon_archived") or state_data.get("issue_closed"))
            pr_number = state_data.get("pr_number")
            issue_closed = state_data.get("issue_closed", False)
            retry_stopped = _load_json(ticket_dir / "retry-state.json").get("stopped", False)

        worker_info = workers.get(ticket_id, {})
        item = BoardItem(
            ticket_id=ticket_id,
            issue_number=issue_number,
            state=state,
            branch=branch,
            worker_pid=worker_info.get("pid"),
            worker_cwd=worker_info.get("worktree_path"),
        )
        if daemon_archived or issue_closed:
            columns["done"].append(item)
        elif state == "TEST_COMPLETE" and pr_number:
            columns["pr_ready"].append(item)
        elif state in _HUMAN_GATE_STATES:
            columns["waiting_human"].append(item)
        elif retry_stopped:
            columns["blocked"].append(item)
        elif ticket_id in workers or (ticket_dir and _lock_held(ticket_dir)):
            columns["running"].append(item)
        else:
            columns["queued"].append(item)

    # Backlog: ai-ready issues not yet ingested — SQLite primary, JSON fallback
    if rdb and db_path:
        issue_index = {str(r["issue_number"]): r["ticket_id"] for r in rdb.list_issue_intake(db_path)}
    else:
        issue_index = _load_issue_index(state_dir) if state_dir.exists() else {}
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
