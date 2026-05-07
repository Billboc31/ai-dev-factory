#!/usr/bin/env python3
"""Sequential ticket runner for ai-dev-factory.

This runner remains intentionally explicit:
- no autonomous merge
- no hidden network calls except explicit git commands
- no prompt generation
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_STEP = ROOT / "run_step.py"


class TicketRunnerError(Exception):
    pass


def validate_ticket_id(ticket_id: str) -> str:
    if not re.fullmatch(r"T\d{3,}", ticket_id):
        raise TicketRunnerError("ticket id must look like T007")
    return ticket_id


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or "work"


def branch_name(ticket_id: str, slug: str | None) -> str:
    suffix = slugify(slug or "work")
    return f"ticket/{ticket_id}-{suffix}"


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        check=False,
    )


def print_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def run_git(args: list[str]) -> int:
    return print_result(run_command(["git", *args]))


def show_next(ticket_id: str) -> int:
    result = run_command([
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        "--next",
    ])
    return print_result(result)


def execute_once(ticket_id: str, step: str, command: str) -> int:
    result = run_command([
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        step,
        "--exec-cmd",
        command,
    ])
    return print_result(result)


def checkout_branch(ticket_id: str, slug: str | None) -> int:
    name = branch_name(ticket_id, slug)
    print(f"checkout branch: {name}")
    exists = run_command(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"])
    if exists.returncode == 0:
        return run_git(["checkout", name])
    return run_git(["checkout", "-b", name])


def commit_ticket(ticket_id: str, message: str | None) -> int:
    default_message = f"{ticket_id}: update agent workflow artifacts"
    commit_message = message or default_message

    run_dir = f"runs/{ticket_id}/"
    print(f"staging: {run_dir}")
    print("note: only runs/ artifacts are auto-staged — stage other changes manually before running --commit")
    add_result = run_command(["git", "add", run_dir])
    print_result(add_result)
    if add_result.returncode != 0:
        return add_result.returncode

    commit_result = run_command(["git", "commit", "-m", commit_message])
    return print_result(commit_result)


def push_branch(ticket_id: str, slug: str | None) -> int:
    name = branch_name(ticket_id, slug)
    print(f"push branch: {name}")
    return run_git(["push", "-u", "origin", name])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sequential ai-dev-factory ticket runner")
    parser.add_argument("ticket_id")
    parser.add_argument("--once", help="Execute a single explicit step")
    parser.add_argument("--exec-cmd", help="External command to execute")
    parser.add_argument("--branch", action="store_true", help="Create or switch to the ticket branch")
    parser.add_argument("--branch-slug", help="Branch suffix after TXXX")
    parser.add_argument("--commit", action="store_true", help="Commit current repo changes")
    parser.add_argument("--commit-message", help="Custom commit message")
    parser.add_argument("--push", action="store_true", help="Push the ticket branch")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        ticket_id = validate_ticket_id(args.ticket_id)

        if args.branch:
            return checkout_branch(ticket_id, args.branch_slug)

        if args.commit:
            return commit_ticket(ticket_id, args.commit_message)

        if args.push:
            return push_branch(ticket_id, args.branch_slug)

        if args.once:
            if not args.exec_cmd:
                print("error: --exec-cmd is required with --once", file=sys.stderr)
                return 2
            return execute_once(ticket_id, args.once, args.exec_cmd)

        return show_next(ticket_id)

    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
