#!/usr/bin/env python3
"""Issue mapper — builds a project-level dependency map from GitHub issues and local run states.

Writes two artifacts:
  runs/.project-map.json          — current snapshot
  runs/.project-map-activity.json — rolling history (max 50 entries)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
PROJECT_MAP_FILENAME = ".project-map.json"
ACTIVITY_FILENAME = ".project-map-activity.json"
ISSUE_INDEX_FILENAME = ".issue-intake.json"
WORKERS_REGISTRY_FILENAME = "workers.json"
MAX_ACTIVITY_ENTRIES = 50
ISSUES_FETCH_LIMIT = 500

AUTO_RUNNABLE_STATES = frozenset({
    "INIT",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_APPROVED",
    "PLAN_FIX_REQUIRED",
    "IMPLEMENTATION_FIX_REQUIRED",
})

HUMAN_GATE_STATES = frozenset({
    "PLAN_REVIEW_NEEDED",
    "TEST_COMPLETE",
})

# Regex patterns for dependency parsing in issue bodies
_DEP_PATTERNS = [
    re.compile(r"(?:depends?\s+on|blocked\s+by|requires?)\s+#(\d+)", re.IGNORECASE),
    re.compile(r"(?:depends?\s+on|blocked\s+by|requires?)\s+T(\d+)\b", re.IGNORECASE),
]
_BLOCKS_PATTERNS = [
    re.compile(r"blocks?\s+#(\d+)", re.IGNORECASE),
    re.compile(r"blocks?\s+T(\d+)\b", re.IGNORECASE),
]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_now_iso()}] [issue-mapper] {msg}", flush=True)


# ── GitHub issue fetching ─────────────────────────────────────────────────────

def fetch_open_issues(repo: str | None) -> list[dict]:
    """Fetch all open issues via gh CLI. Returns [] on failure."""
    cmd = [
        "gh", "issue", "list",
        "--state", "open",
        "--json", "number,title,body,labels",
        "--limit", str(ISSUES_FETCH_LIMIT),
    ]
    if repo:
        cmd += ["--repo", repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"gh issue list failed (rc={result.returncode}): {result.stderr.strip()}")
            return []
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except FileNotFoundError:
        _log("gh not found — cannot fetch issues")
        return []
    except json.JSONDecodeError:
        _log("gh returned invalid JSON")
        return []


# ── Dependency parsing ────────────────────────────────────────────────────────

def _parse_issue_refs(text: str) -> list[int]:
    """Return list of GitHub issue numbers referenced as dependencies in text."""
    refs: list[int] = []
    for pattern in _DEP_PATTERNS:
        for m in pattern.finditer(text):
            try:
                refs.append(int(m.group(1)))
            except ValueError:
                pass
    return list(dict.fromkeys(refs))  # deduplicate preserving order


def _parse_blocks_refs(text: str) -> list[int]:
    """Return list of GitHub issue numbers that this issue explicitly blocks."""
    refs: list[int] = []
    for pattern in _BLOCKS_PATTERNS:
        for m in pattern.finditer(text):
            try:
                refs.append(int(m.group(1)))
            except ValueError:
                pass
    return list(dict.fromkeys(refs))


# ── Local state reading ───────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_issue_index(runs_dir: Path) -> dict[str, str]:
    """Returns {issue_number_str: ticket_id}."""
    data = _load_json(runs_dir / ISSUE_INDEX_FILENAME)
    if isinstance(data, dict):
        return data
    return {}


def load_workers_registry(runs_dir: Path) -> dict[str, dict]:
    data = _load_json(runs_dir / WORKERS_REGISTRY_FILENAME)
    if isinstance(data, dict):
        return data
    return {}


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def load_local_ticket_states(runs_dir: Path, worktrees_dir: Path | None) -> dict[str, dict]:
    """Returns {ticket_id: state_dict} for all locally known tickets."""
    states: dict[str, dict] = {}

    if worktrees_dir and worktrees_dir.exists():
        for wt_dir in sorted(worktrees_dir.iterdir()):
            tid = wt_dir.name
            if not re.match(r"^T\d{3,}$", tid):
                continue
            sp = wt_dir / "runs" / tid / "state.json"
            data = _load_json(sp)
            if isinstance(data, dict) and data.get("ticket_id"):
                states[tid] = data

    for sp in sorted(runs_dir.glob("*/state.json")):
        tid = sp.parent.name
        if tid in states:
            continue
        data = _load_json(sp)
        if isinstance(data, dict) and data.get("ticket_id"):
            states[tid] = data

    return states


def _get_run_dir(ticket_id: str, runs_dir: Path, worktrees_dir: Path | None) -> Path:
    if worktrees_dir:
        wt = worktrees_dir / ticket_id / "runs" / ticket_id
        if wt.exists():
            return wt
    return runs_dir / ticket_id


def _is_retry_blocked(run_dir: Path) -> bool:
    retry_path = run_dir / "retry-state.json"
    data = _load_json(retry_path)
    if isinstance(data, dict):
        return bool(data.get("stopped"))
    return False


def _is_worker_running(ticket_id: str, workers: dict[str, dict]) -> bool:
    entry = workers.get(ticket_id)
    if not entry:
        return False
    pid = entry.get("pid")
    if isinstance(pid, int):
        return _is_pid_alive(pid)
    return False


# ── Status classification ─────────────────────────────────────────────────────

def classify_ticket_status(
    ticket_id: str | None,
    issue_number: int,
    runs_dir: Path,
    worktrees_dir: Path | None,
    local_states: dict[str, dict],
    workers: dict[str, dict],
    dep_issue_numbers: list[int],
    issue_index: dict[str, str],
    issue_status_map: dict[int, str],
) -> str:
    """Classify a ticket/issue into one of the known statuses."""
    if ticket_id is None:
        return "not_ingested"

    state_data = local_states.get(ticket_id)
    if state_data is None:
        return "not_ingested"

    if state_data.get("daemon_archived") or state_data.get("issue_closed"):
        return "done"

    if _is_worker_running(ticket_id, workers):
        return "running"

    ticket_state = state_data.get("state", "")

    run_dir = _get_run_dir(ticket_id, runs_dir, worktrees_dir)
    if _is_retry_blocked(run_dir):
        return "blocked_retry"

    # Check if any dependency is not done
    for dep_issue_num in dep_issue_numbers:
        dep_status = issue_status_map.get(dep_issue_num)
        if dep_status is not None and dep_status != "done":
            return "blocked_dependency"
        # If dep_status is None, the dep issue isn't in our open issues list —
        # assume it might be closed (done) on GitHub
        dep_ticket_id = issue_index.get(str(dep_issue_num))
        if dep_ticket_id:
            dep_state = local_states.get(dep_ticket_id, {})
            if not (dep_state.get("daemon_archived") or dep_state.get("issue_closed")):
                dep_ticket_state = dep_state.get("state", "")
                if dep_ticket_state and dep_ticket_state not in ("TEST_COMPLETE",):
                    return "blocked_dependency"

    if ticket_state in HUMAN_GATE_STATES:
        return "waiting_human"

    if ticket_state in AUTO_RUNNABLE_STATES:
        return "runnable"

    return "not_ingested"


# ── Cycle detection ───────────────────────────────────────────────────────────

def detect_cycles(depends_on: dict[str, list[str]]) -> list[list[str]]:
    """Return list of cycles (each cycle is a list of ticket IDs). Uses DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    path: list[str] = []
    cycles: list[list[str]] = []

    all_nodes = set(depends_on.keys())
    for deps in depends_on.values():
        all_nodes.update(deps)

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in depends_on.get(node, []):
            if color.get(neighbor) == GRAY:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color.get(neighbor, WHITE) == WHITE:
                dfs(neighbor)
        path.pop()
        color[node] = BLACK

    for node in sorted(all_nodes):
        if color.get(node, WHITE) == WHITE:
            dfs(node)

    return cycles


# ── Parallelizable group detection ───────────────────────────────────────────

def compute_parallelizable_groups(
    ticket_statuses: dict[str, str],
    depends_on: dict[str, list[str]],
) -> list[list[str]]:
    """Return groups of runnable tickets that can safely run in parallel.

    A group contains tickets that:
    - are all 'runnable'
    - have no dependency between any two members of the same group
    - all their dependencies are 'done' (or have no local state = assumed done)
    """
    runnable = [tid for tid, s in ticket_statuses.items() if s == "runnable"]

    # Filter to immediately runnable: all deps done
    immediately_runnable = []
    for tid in runnable:
        deps = depends_on.get(tid, [])
        all_deps_done = all(
            ticket_statuses.get(dep) in ("done", None)
            for dep in deps
        )
        if all_deps_done:
            immediately_runnable.append(tid)

    if not immediately_runnable:
        return []

    # Build adjacency for the dependency sub-graph among immediately_runnable
    runnable_set = set(immediately_runnable)
    has_dep: dict[str, set[str]] = {tid: set() for tid in immediately_runnable}
    for tid in immediately_runnable:
        for dep in depends_on.get(tid, []):
            if dep in runnable_set:
                has_dep[tid].add(dep)
        for other in immediately_runnable:
            if tid in depends_on.get(other, []):
                has_dep[other].add(tid)

    # Find connected components via union-find
    parent = {tid: tid for tid in immediately_runnable}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    for tid in immediately_runnable:
        for dep in has_dep[tid]:
            union(tid, dep)

    groups: dict[str, list[str]] = {}
    for tid in sorted(immediately_runnable):
        root = find(tid)
        groups.setdefault(root, []).append(tid)

    return sorted(groups.values(), key=lambda g: g[0])


# ── next_recommended ──────────────────────────────────────────────────────────

def _ticket_sort_key(ticket_id: str) -> int:
    m = re.match(r"T(\d+)$", ticket_id)
    return int(m.group(1)) if m else 999999


def compute_next_recommended(
    ticket_statuses: dict[str, str],
    depends_on: dict[str, list[str]],
) -> str | None:
    """Return the lowest-numbered runnable ticket whose deps are all done."""
    candidates = [
        tid for tid, s in ticket_statuses.items()
        if s == "runnable"
        and all(
            ticket_statuses.get(dep) in ("done", None)
            for dep in depends_on.get(tid, [])
        )
    ]
    if not candidates:
        return None
    return min(candidates, key=_ticket_sort_key)


# ── Ambiguity detection ───────────────────────────────────────────────────────

def detect_ambiguities(
    issues: list[dict],
    issue_index: dict[str, str],
    dep_map: dict[int, list[int]],
) -> list[dict]:
    """Detect issues with ambiguous or unresolvable dependencies."""
    ambiguities = []
    issue_numbers = {i["number"] for i in issues}

    for issue in issues:
        for dep_num in dep_map.get(issue["number"], []):
            if dep_num not in issue_numbers and str(dep_num) not in issue_index:
                ambiguities.append({
                    "issue": issue["number"],
                    "detail": f"depends on #{dep_num} which is not in open issues and not ingested",
                })
    return ambiguities


# ── Output writers ────────────────────────────────────────────────────────────

def _atomic_write(path: Path, data: dict | list) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_project_map(runs_dir: Path, map_data: dict) -> None:
    _atomic_write(runs_dir / PROJECT_MAP_FILENAME, map_data)
    _log(f"wrote {PROJECT_MAP_FILENAME}")


def write_activity(runs_dir: Path, entry: dict) -> None:
    path = runs_dir / ACTIVITY_FILENAME
    existing = _load_json(path)
    entries: list[dict] = existing if isinstance(existing, list) else []
    entries.append(entry)
    if len(entries) > MAX_ACTIVITY_ENTRIES:
        entries = entries[-MAX_ACTIVITY_ENTRIES:]
    _atomic_write(path, entries)
    _log(f"wrote activity entry ({len(entries)} total)")


# ── Main logic ────────────────────────────────────────────────────────────────

def run_mapper(
    runs_dir: Path,
    repo: str | None,
    worktrees_dir: Path | None = None,
) -> None:
    _log(f"starting issue mapper runs_dir={runs_dir} repo={repo!r}")

    issues = fetch_open_issues(repo)
    _log(f"fetched {len(issues)} open issues")

    issue_index = load_issue_index(runs_dir)
    local_states = load_local_ticket_states(runs_dir, worktrees_dir)
    workers = load_workers_registry(runs_dir)

    # Build issue_number -> issue dict
    issue_map: dict[int, dict] = {i["number"]: i for i in issues}

    # Parse dependencies from issue bodies
    # dep_map: issue_number -> list of issue_numbers it depends on
    dep_map: dict[int, list[int]] = {}
    blocks_map: dict[int, list[int]] = {}  # issue_number -> issues it blocks

    for issue in issues:
        body = issue.get("body") or ""
        title = issue.get("title") or ""
        text = f"{title}\n{body}"
        deps = _parse_issue_refs(text)
        if deps:
            dep_map[issue["number"]] = deps
        blocks = _parse_blocks_refs(text)
        if blocks:
            blocks_map[issue["number"]] = blocks

    # Merge reverse "blocks" into "depends_on"
    for issue_num, blocked_list in blocks_map.items():
        for blocked_issue in blocked_list:
            existing = dep_map.get(blocked_issue, [])
            if issue_num not in existing:
                existing.append(issue_num)
            dep_map[blocked_issue] = existing

    # Map issue numbers to ticket IDs
    # issue_to_ticket: issue_number -> ticket_id (or None)
    issue_to_ticket: dict[int, str | None] = {}
    for issue in issues:
        ticket_id = issue_index.get(str(issue["number"]))
        issue_to_ticket[issue["number"]] = ticket_id

    # Build ticket_id -> list[ticket_id] dependency graph
    depends_on_tickets: dict[str, list[str]] = {}
    for issue_num, dep_issue_nums in dep_map.items():
        ticket_id = issue_to_ticket.get(issue_num)
        if ticket_id is None:
            continue
        dep_tids = []
        for dep_num in dep_issue_nums:
            dep_tid = issue_to_ticket.get(dep_num)
            if dep_tid:
                dep_tids.append(dep_tid)
        if dep_tids:
            depends_on_tickets[ticket_id] = dep_tids

    # Two-pass status classification: first pass without dep awareness, second pass with
    # Pass 1: compute basic statuses
    ticket_statuses: dict[str, str] = {}
    for issue in issues:
        issue_num = issue["number"]
        ticket_id = issue_to_ticket.get(issue_num)
        ticket_statuses[issue_num] = classify_ticket_status(
            ticket_id=ticket_id,
            issue_number=issue_num,
            runs_dir=runs_dir,
            worktrees_dir=worktrees_dir,
            local_states=local_states,
            workers=workers,
            dep_issue_numbers=[],  # no dep check in pass 1
            issue_index=issue_index,
            issue_status_map={},
        )

    # Pass 2: refine with dependency-awareness
    for issue in issues:
        issue_num = issue["number"]
        ticket_id = issue_to_ticket.get(issue_num)
        ticket_statuses[issue_num] = classify_ticket_status(
            ticket_id=ticket_id,
            issue_number=issue_num,
            runs_dir=runs_dir,
            worktrees_dir=worktrees_dir,
            local_states=local_states,
            workers=workers,
            dep_issue_numbers=dep_map.get(issue_num, []),
            issue_index=issue_index,
            issue_status_map=ticket_statuses,
        )

    # Build ticket_id keyed status map for the graph functions
    ticket_id_statuses: dict[str, str] = {}
    for issue_num, status in ticket_statuses.items():
        tid = issue_to_ticket.get(issue_num)
        if tid:
            ticket_id_statuses[tid] = status

    cycles = detect_cycles(depends_on_tickets)
    if cycles:
        _log(f"detected {len(cycles)} cycle(s) in dependency graph")

    parallelizable_groups = compute_parallelizable_groups(ticket_id_statuses, depends_on_tickets)
    next_recommended = compute_next_recommended(ticket_id_statuses, depends_on_tickets)
    ambiguities = detect_ambiguities(issues, issue_index, dep_map)

    if next_recommended:
        _log(f"next_recommended={next_recommended}")
    _log(f"parallelizable_groups={len(parallelizable_groups)} runnable={sum(1 for s in ticket_id_statuses.values() if s == 'runnable')}")

    # Build ticket entries for the map
    ticket_entries = []
    for issue in sorted(issues, key=lambda i: i["number"]):
        issue_num = issue["number"]
        ticket_id = issue_to_ticket.get(issue_num)
        status = ticket_statuses.get(issue_num, "not_ingested")
        dep_issue_nums = dep_map.get(issue_num, [])
        dep_ticket_ids = [
            issue_to_ticket[n] for n in dep_issue_nums
            if issue_to_ticket.get(n)
        ]
        blocked_issues = [
            n for n in dep_issue_nums
            if ticket_statuses.get(n) not in ("done", None)
            and n != issue_num
        ]
        ticket_entries.append({
            "ticket_id": ticket_id,
            "issue_number": issue_num,
            "title": issue.get("title"),
            "status": status,
            "depends_on": dep_ticket_ids,
            "depends_on_issues": dep_issue_nums,
            "blocks": [
                issue_to_ticket.get(n) for n in blocks_map.get(issue_num, [])
                if issue_to_ticket.get(n)
            ],
            "ambiguities": [
                a["detail"] for a in ambiguities if a["issue"] == issue_num
            ],
        })

    summary = {
        "total": len(issues),
        "done": sum(1 for s in ticket_statuses.values() if s == "done"),
        "running": sum(1 for s in ticket_statuses.values() if s == "running"),
        "waiting_human": sum(1 for s in ticket_statuses.values() if s == "waiting_human"),
        "runnable": sum(1 for s in ticket_statuses.values() if s == "runnable"),
        "blocked": sum(1 for s in ticket_statuses.values() if s in ("blocked_dependency", "blocked_retry")),
        "not_ingested": sum(1 for s in ticket_statuses.values() if s == "not_ingested"),
    }

    map_data = {
        "generated_at": _now_iso(),
        "tickets": ticket_entries,
        "parallelizable_groups": parallelizable_groups,
        "next_recommended": next_recommended,
        "cycles": cycles,
        "summary": summary,
    }

    activity_entry = {
        "timestamp": _now_iso(),
        "total_issues": len(issues),
        "runnable": [tid for tid, s in ticket_id_statuses.items() if s == "runnable"],
        "blocked": [tid for tid, s in ticket_id_statuses.items() if s in ("blocked_dependency", "blocked_retry")],
        "parallelizable_groups": parallelizable_groups,
        "next_recommended": next_recommended,
        "cycles": cycles,
        "ambiguities": ambiguities,
        "summary": summary,
    }

    write_project_map(runs_dir, map_data)
    write_activity(runs_dir, activity_entry)
    _log("done")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Issue mapper — build project dependency map")
    parser.add_argument("--runs-dir", default="runs", help="Path to runs directory (default: runs)")
    parser.add_argument("--repo", default=None, help="GitHub repo (owner/repo)")
    parser.add_argument("--worktrees-dir", default=None, help="Base directory for per-ticket worktrees")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        print(f"error: runs dir not found: {runs_dir}", file=sys.stderr)
        return 2
    worktrees_dir = Path(args.worktrees_dir) if args.worktrees_dir else None
    run_mapper(runs_dir, repo=args.repo, worktrees_dir=worktrees_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
