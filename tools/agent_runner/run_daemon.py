#!/usr/bin/env python3
"""Local workflow daemon for ai-dev-factory.

Polls runs/*/state.json and launches run_ticket.py --auto for auto-runnable states.
Never bypasses human gate states.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_TICKET = ROOT / "run_ticket.py"
RUN_ISSUE_INTAKE = ROOT / "run_issue_intake.py"
ISSUE_INDEX_FILENAME = ".issue-intake.json"

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


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(message: str) -> None:
    print(f"[{_now_iso()}] [daemon] {message}", flush=True)


def _lock_path(run_dir: Path) -> Path:
    return run_dir / "daemon.lock"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(run_dir: Path) -> bool:
    """Try to acquire daemon.lock. Returns True if acquired, False if held by a live process."""
    lock = _lock_path(run_dir)
    if lock.exists():
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if isinstance(pid, int) and _is_pid_alive(pid):
                return False
            _log(f"cleaning stale lock for {run_dir.name} (pid={pid})")
            lock.unlink()
        except (json.JSONDecodeError, OSError):
            try:
                lock.unlink()
            except OSError:
                pass
    try:
        lock.write_text(
            json.dumps({"pid": os.getpid(), "created_at": _now_iso()}),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def _release_lock(run_dir: Path) -> None:
    try:
        _lock_path(run_dir).unlink()
    except OSError:
        pass


def scan_tickets(runs_dir: Path) -> list[tuple[str, str]]:
    """Return (ticket_id, state) for all readable state.json files, sorted by ticket_id."""
    results = []
    for state_path in sorted(runs_dir.glob("*/state.json")):
        ticket_id = state_path.parent.name
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            state = data.get("state", "")
            if state:
                results.append((ticket_id, state))
        except (json.JSONDecodeError, OSError):
            _log(f"skipping {ticket_id}: corrupted or unreadable state.json")
    return results


def launch_ticket(ticket_id: str, exec_cmd: str, dry_run: bool, runs_dir: Path) -> None:
    """Launch run_ticket.py --auto for one ticket. No-op in dry_run mode."""
    run_dir = runs_dir / ticket_id

    if dry_run:
        _log(f"dry-run: would launch {ticket_id} --auto --exec-cmd {exec_cmd!r}")
        return

    if not _acquire_lock(run_dir):
        _log(f"skipping {ticket_id}: already running (lock held)")
        return

    try:
        _log(f"launching {ticket_id} --auto")
        result = subprocess.run(
            [sys.executable, str(RUN_TICKET), ticket_id, "--auto", "--exec-cmd", exec_cmd],
            text=True,
            capture_output=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            _log(f"{ticket_id}: {line}")
        for line in result.stderr.splitlines():
            _log(f"{ticket_id} [err]: {line}")
        _log(f"{ticket_id}: done rc={result.returncode}")
    finally:
        _release_lock(run_dir)


# ── issue polling ─────────────────────────────────────────────────────────────

def load_issue_index(runs_dir: Path) -> dict[str, str]:
    """Load the anti-duplicate index mapping issue numbers to ticket IDs."""
    path = runs_dir / ISSUE_INDEX_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_issue_index(runs_dir: Path, index: dict[str, str]) -> None:
    """Persist the anti-duplicate index atomically via a temp file rename."""
    path = runs_dir / ISSUE_INDEX_FILENAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=2), encoding="utf-8")
    tmp.replace(path)


def next_ticket_id(runs_dir: Path, reserved: set[str] | None = None) -> str:
    """Compute the next available ticket ID by scanning runs/T*/ and the optional reserved set."""
    max_num = 0
    for p in runs_dir.glob("T*/"):
        m = re.match(r"T(\d+)$", p.name)
        if m:
            max_num = max(max_num, int(m.group(1)))
    for tid in (reserved or ()):
        m = re.match(r"T(\d+)$", tid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"T{max_num + 1:03d}"


def slugify_title(title: str) -> str:
    """Convert an issue title to a URL-safe branch slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:50].rstrip("-")
    return slug or "issue"


def fetch_ready_issues(label: str, repo: str | None) -> list[dict]:
    """Call `gh issue list` and return open issues with the given label. Returns [] on any failure."""
    cmd = ["gh", "issue", "list", "--label", label, "--json", "number,title", "--state", "open"]
    if repo:
        cmd += ["--repo", repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"gh issue list failed (rc={result.returncode}) — skipping issue polling")
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except FileNotFoundError:
        _log("gh not found — skipping issue polling")
        return []
    except json.JSONDecodeError:
        _log("gh returned invalid JSON — skipping issue polling")
        return []


def call_issue_intake(issue_number: int, ticket_id: str, branch_slug: str, repo: str | None) -> bool:
    """Run run_issue_intake.py for one issue. Returns True on success."""
    cmd = [
        sys.executable, str(RUN_ISSUE_INTAKE),
        "--issue", str(issue_number),
        "--ticket-id", ticket_id,
        "--branch-slug", branch_slug,
    ]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        _log(f"intake {ticket_id}: {line}")
    for line in result.stderr.splitlines():
        _log(f"intake {ticket_id} [err]: {line}")
    return result.returncode == 0


def poll_github_issues(runs_dir: Path, label: str, repo: str | None) -> None:
    """Detect ready GitHub issues and create local runs for new ones."""
    issues = fetch_ready_issues(label, repo)
    if not issues:
        _log(f"no issues found with label={label!r}")
        return

    index = load_issue_index(runs_dir)
    _log(f"found {len(issues)} issue(s) with label={label!r}")

    for issue in issues:
        number = str(issue["number"])
        title = issue.get("title", "")

        if number in index:
            _log(f"issue #{number} already ingested as {index[number]} — skipping")
            continue

        ticket_id = next_ticket_id(runs_dir, reserved=set(index.values()))
        slug = slugify_title(title)
        _log(f"ingesting issue #{number} ({title!r}) as {ticket_id} slug={slug!r}")

        if call_issue_intake(int(number), ticket_id, slug, repo):
            index[number] = ticket_id
            save_issue_index(runs_dir, index)
            _log(f"issue #{number} ingested as {ticket_id}")
        else:
            _log(f"intake failed for issue #{number} — will retry next cycle")


def run_once(exec_cmd: str, dry_run: bool, runs_dir: Path) -> None:
    """Scan all tickets and process auto-runnable ones."""
    tickets = scan_tickets(runs_dir)
    if not tickets:
        _log("no tickets found")
        return
    for ticket_id, state in tickets:
        if state in AUTO_RUNNABLE_STATES:
            _log(f"detected {ticket_id} state={state}")
            launch_ticket(ticket_id, exec_cmd, dry_run, runs_dir)
        elif state in HUMAN_GATE_STATES:
            _log(f"skipping {ticket_id} state={state} (human gate)")
        else:
            _log(f"skipping {ticket_id} state={state}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local workflow daemon for ai-dev-factory")
    parser.add_argument("--exec-cmd", required=True, help="Command passed to run_ticket.py --auto")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without executing")
    parser.add_argument("--runs-dir", default="runs", help="Path to runs directory (default: runs)")
    parser.add_argument("--poll-issues", action="store_true", help="Enable GitHub issue polling")
    parser.add_argument("--issue-label", default="ai-ready", help="GitHub label to filter issues (default: ai-ready)")
    parser.add_argument("--issue-repo", default=None, help="GitHub repo (owner/repo) — defaults to current repo")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)

    if not runs_dir.exists():
        print(f"error: runs dir not found: {runs_dir}", file=sys.stderr)
        return 2

    _log(f"starting daemon exec-cmd={args.exec_cmd!r} interval={args.interval}s dry-run={args.dry_run}")
    if args.poll_issues:
        _log(f"issue polling enabled label={args.issue_label!r} repo={args.issue_repo!r}")

    if args.once:
        if args.poll_issues:
            poll_github_issues(runs_dir, args.issue_label, args.issue_repo)
        run_once(args.exec_cmd, args.dry_run, runs_dir)
        return 0

    try:
        while True:
            if args.poll_issues:
                poll_github_issues(runs_dir, args.issue_label, args.issue_repo)
            run_once(args.exec_cmd, args.dry_run, runs_dir)
            _log(f"sleeping {args.interval}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        _log("interrupted — daemon stopping")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
