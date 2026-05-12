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
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_TICKET = ROOT / "run_ticket.py"

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
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)

    if not runs_dir.exists():
        print(f"error: runs dir not found: {runs_dir}", file=sys.stderr)
        return 2

    _log(f"starting daemon exec-cmd={args.exec_cmd!r} interval={args.interval}s dry-run={args.dry_run}")

    if args.once:
        run_once(args.exec_cmd, args.dry_run, runs_dir)
        return 0

    try:
        while True:
            run_once(args.exec_cmd, args.dry_run, runs_dir)
            _log(f"sleeping {args.interval}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        _log("interrupted — daemon stopping")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
