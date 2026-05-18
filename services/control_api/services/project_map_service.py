"""Read-only service for project map artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..models.schemas import (
    ProjectMapActivityEntry,
    ProjectMapActivityResponse,
    ProjectMapResponse,
    ProjectMapSummary,
    ProjectMapTicket,
)

_PROJECT_MAP_FILE = ".project-map.json"
_ACTIVITY_FILE = ".project-map-activity.json"


def _runs_dir(project_root: Path) -> Path:
    return project_root / "runs"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_project_map(project_root: Path) -> ProjectMapResponse:
    data = _load_json(_runs_dir(project_root) / _PROJECT_MAP_FILE)
    if not isinstance(data, dict):
        return ProjectMapResponse()

    tickets = [
        ProjectMapTicket(
            ticket_id=t.get("ticket_id"),
            issue_number=t.get("issue_number"),
            title=t.get("title"),
            status=t.get("status", "unknown"),
            depends_on=t.get("depends_on") or [],
            depends_on_issues=t.get("depends_on_issues") or [],
            blocks=t.get("blocks") or [],
            ambiguities=t.get("ambiguities") or [],
        )
        for t in (data.get("tickets") or [])
    ]

    raw_summary = data.get("summary") or {}
    summary = ProjectMapSummary(
        total=raw_summary.get("total", 0),
        done=raw_summary.get("done", 0),
        running=raw_summary.get("running", 0),
        waiting_human=raw_summary.get("waiting_human", 0),
        runnable=raw_summary.get("runnable", 0),
        blocked=raw_summary.get("blocked", 0),
        not_ingested=raw_summary.get("not_ingested", 0),
    )

    return ProjectMapResponse(
        generated_at=data.get("generated_at"),
        tickets=tickets,
        parallelizable_groups=data.get("parallelizable_groups") or [],
        next_recommended=data.get("next_recommended"),
        cycles=data.get("cycles") or [],
        summary=summary,
    )


def get_project_map_activity(project_root: Path) -> ProjectMapActivityResponse:
    data = _load_json(_runs_dir(project_root) / _ACTIVITY_FILE)
    if not isinstance(data, list):
        return ProjectMapActivityResponse()

    entries = []
    for raw in reversed(data):  # most recent first
        if not isinstance(raw, dict):
            continue
        entries.append(ProjectMapActivityEntry(
            timestamp=raw.get("timestamp", ""),
            total_issues=raw.get("total_issues", 0),
            runnable=raw.get("runnable") or [],
            blocked=raw.get("blocked") or [],
            parallelizable_groups=raw.get("parallelizable_groups") or [],
            next_recommended=raw.get("next_recommended"),
            cycles=raw.get("cycles") or [],
            ambiguities=raw.get("ambiguities") or [],
            summary=raw.get("summary"),
        ))

    return ProjectMapActivityResponse(entries=entries)


def refresh_project_map(project_root: Path, repo: str | None = None) -> bool:
    """Trigger run_issue_mapper.py synchronously. Returns True on success."""
    mapper = Path(__file__).resolve().parent.parent.parent.parent / "tools" / "agent_runner" / "run_issue_mapper.py"
    if not mapper.exists():
        return False
    cmd = [sys.executable, str(mapper), "--runs-dir", str(_runs_dir(project_root))]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(project_root))
    return result.returncode == 0
