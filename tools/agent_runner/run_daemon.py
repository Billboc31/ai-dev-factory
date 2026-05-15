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
RETRY_STATE_FILENAME = "retry-state.json"

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

# Retry/cooldown policies per failure class.
# Keys match the categories produced by classify_runtime_failure in run_step.py.
_RETRY_POLICIES: dict[str, dict] = {
    "quota_exceeded":          {"action": "cooldown",    "cooldown_seconds": 3600},
    "provider_error":          {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_crashed":         {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_failed":          {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    "empty_output":            {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    "write_permission_missing": {"action": "stop"},
    "unknown":                 {"action": "stop"},
}


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


# ── retry / cooldown state ────────────────────────────────────────────────────

def _retry_state_path(run_dir: Path) -> Path:
    return run_dir / RETRY_STATE_FILENAME


def _load_retry_state(run_dir: Path) -> dict:
    path = _retry_state_path(run_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_retry_state(run_dir: Path, state: dict) -> None:
    path = _retry_state_path(run_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _clear_retry_state(run_dir: Path) -> None:
    try:
        _retry_state_path(run_dir).unlink()
    except OSError:
        pass


def _read_last_failure_class(run_dir: Path) -> str | None:
    """Return the last failure class logged in runtime.log, or None."""
    log_path = run_dir / "runtime.log"
    if not log_path.exists():
        return None
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return None
    last_class = None
    for line in content.splitlines():
        m = re.search(r"runtime failure: (\w+)", line)
        if m:
            last_class = m.group(1)
    return last_class


def _cooldown_until(seconds: int) -> str:
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply_retry_policy(ticket_id: str, failure_class: str, retry_state: dict) -> dict:
    """Return an updated retry_state dict after applying the policy for failure_class."""
    policy = _RETRY_POLICIES.get(failure_class, {"action": "stop"})
    action = policy["action"]
    new_state: dict = dict(retry_state)
    new_state["failure_class"] = failure_class
    new_state.setdefault("retry_count", 0)

    if action == "stop":
        new_state["stopped"] = True
        new_state["stop_reason"] = failure_class
        _log(f"{ticket_id}: retry policy=stop failure={failure_class} — requires human attention")

    elif action == "cooldown":
        seconds = policy["cooldown_seconds"]
        new_state["cooldown_until"] = _cooldown_until(seconds)
        new_state.pop("stopped", None)
        _log(f"{ticket_id}: retry policy=cooldown failure={failure_class} cooldown={seconds}s until={new_state['cooldown_until']}")

    elif action == "exponential":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            fallback = policy["fallback_cooldown_seconds"]
            new_state["cooldown_until"] = _cooldown_until(fallback)
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} max_retries={max_retries} reached — cooldown {fallback}s")
        else:
            delay = policy["base_seconds"] * (2 ** count)
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    elif action == "fixed_delay":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            new_state["stopped"] = True
            new_state["stop_reason"] = f"{failure_class}_max_retries"
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} max_retries={max_retries} reached — stopped")
        else:
            delay = policy["delay_seconds"]
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    return new_state


def _is_blocked_by_retry(ticket_id: str, retry_state: dict) -> bool:
    """Return True and log if the ticket must be skipped due to retry/cooldown state."""
    if retry_state.get("stopped"):
        reason = retry_state.get("stop_reason", "unknown")
        _log(f"skipping {ticket_id}: stopped reason={reason} — requires human attention")
        return True
    cooldown_until = retry_state.get("cooldown_until")
    if cooldown_until:
        try:
            until_dt = datetime.datetime.strptime(cooldown_until, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < until_dt:
                remaining = int((until_dt - now).total_seconds())
                _log(f"skipping {ticket_id}: in cooldown until={cooldown_until} remaining={remaining}s")
                return True
        except ValueError:
            pass
    return False


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
        if result.returncode != 0:
            failure_class = _read_last_failure_class(run_dir)
            if failure_class:
                retry_state = _load_retry_state(run_dir)
                retry_state = _apply_retry_policy(ticket_id, failure_class, retry_state)
                _save_retry_state(run_dir, retry_state)
            else:
                _log(f"{ticket_id}: no failure class in runtime.log — retry policy not applied")
        else:
            _clear_retry_state(run_dir)
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
            run_dir = runs_dir / ticket_id
            retry_state = _load_retry_state(run_dir)
            if _is_blocked_by_retry(ticket_id, retry_state):
                continue
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
