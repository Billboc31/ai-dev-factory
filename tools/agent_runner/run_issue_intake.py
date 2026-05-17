#!/usr/bin/env python3
"""GitHub issue intake for ai-dev-factory.

Transforms a GitHub Issue into a local run directory ready for run_ticket.py.

Does NOT execute workflow steps — that is run_ticket.py's responsibility.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(ticket_id: str, message: str) -> None:
    log_path = Path("runs") / ticket_id / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] {message}\n")


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


class IntakeError(Exception):
    pass


def validate_ticket_id(ticket_id: str) -> str:
    if not re.fullmatch(r"T\d{3,}", ticket_id):
        raise IntakeError(f"invalid ticket-id {ticket_id!r} — expected pattern like T007")
    return ticket_id


def check_state_absent(ticket_id: str) -> None:
    path = Path("runs") / ticket_id / "state.json"
    if path.exists():
        raise IntakeError(
            f"state.json already exists at {path} — delete it first to re-initialize"
        )


def check_working_tree_clean() -> None:
    result = _run(["git", "status", "--porcelain"])
    if result.returncode != 0:
        raise IntakeError("failed to check git status")
    if result.stdout.strip():
        raise IntakeError("working tree is not clean — commit or stash changes first")


def get_current_branch() -> str | None:
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def return_to_branch(branch: str) -> None:
    result = _run(["git", "checkout", branch])
    if result.returncode != 0:
        print(f"warning: failed to return to branch {branch!r}: {result.stderr.strip()}", file=sys.stderr)


def fetch_issue(issue_number: int, repo: str | None) -> dict[str, str]:
    cmd = ["gh", "issue", "view", str(issue_number), "--json", "title,body"]
    if repo:
        cmd += ["--repo", repo]
    result = _run(cmd)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        hint = " (run 'gh auth login' if not authenticated)" if "auth" in stderr.lower() else ""
        raise IntakeError(f"gh issue view failed{hint}: {stderr}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise IntakeError(f"gh output is not valid JSON: {exc}") from exc
    return {"title": data.get("title", ""), "body": data.get("body", "")}


def branch_name(ticket_id: str, slug: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", slug.strip().lower()).strip("-") or "work"
    return f"ticket/{ticket_id}-{safe}"


def create_branch(name: str) -> None:
    exists = _run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"])
    if exists.returncode == 0:
        raise IntakeError(
            f"branch {name!r} already exists — delete it first or choose a different slug"
        )
    result = _run(["git", "checkout", "-b", name])
    if result.returncode != 0:
        raise IntakeError(f"failed to create branch {name!r}: {result.stderr.strip()}")


def write_ticket_md(ticket_id: str, issue_number: int, title: str, body: str) -> None:
    dest = Path("runs") / ticket_id / "ticket.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# {ticket_id} — {title}\n\n"
        f"**Source**: GitHub Issue #{issue_number}\n\n"
        f"## Description\n\n"
        f"{body.strip()}\n"
    )
    dest.write_text(content, encoding="utf-8")


def commit_bootstrap(ticket_id: str, push: bool = False) -> None:
    """Stage runs/TXXX/ticket.md + state.json and commit as bootstrap checkpoint."""
    paths_to_stage = [
        f"runs/{ticket_id}/ticket.md",
        f"runs/{ticket_id}/state.json",
    ]
    for path in paths_to_stage:
        add_result = _run(["git", "add", path])
        if add_result.returncode != 0:
            stderr = add_result.stderr.strip()
            _log(ticket_id, f"bootstrap checkpoint: failed to stage {path}: {stderr}")
            print(f"warning: bootstrap checkpoint: failed to stage {path}", file=sys.stderr)
            return
    message = f"{ticket_id}: bootstrap checkpoint"
    commit_result = _run(["git", "commit", "-m", message])
    if commit_result.returncode != 0:
        stderr = (commit_result.stderr or commit_result.stdout).strip()
        _log(ticket_id, f"bootstrap checkpoint: commit failed: {stderr}")
        print(f"warning: bootstrap checkpoint commit failed: {stderr}", file=sys.stderr)
        return
    _log(ticket_id, "bootstrap checkpoint completed")
    print(f"bootstrap checkpoint completed for {ticket_id}")
    if push:
        push_result = _run(["git", "push", "-u", "origin", "HEAD"])
        if push_result.returncode != 0:
            stderr = push_result.stderr.strip()
            _log(ticket_id, f"checkpoint push for {ticket_id}: failed: {stderr}")
            print(f"warning: checkpoint push failed: {stderr}", file=sys.stderr)
        else:
            _log(ticket_id, f"checkpoint push for {ticket_id}")
            print(f"checkpoint push for {ticket_id}")


def write_state_json(ticket_id: str, branch: str, issue_number: int) -> None:
    path = Path("runs") / ticket_id / "state.json"
    state = {
        "ticket_id": ticket_id,
        "state": "INIT",
        "branch": branch,
        "issue_number": issue_number,
        "updated_at": _now_iso(),
    }
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.rename(path)


def run_intake(
    ticket_id: str,
    issue_number: int,
    branch_slug: str,
    repo: str | None,
    push: bool = False,
) -> int:
    try:
        validate_ticket_id(ticket_id)
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        check_state_absent(ticket_id)
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        check_working_tree_clean()
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    original_branch = get_current_branch()

    print(f"fetching GitHub issue #{issue_number}...")
    try:
        issue = fetch_issue(issue_number, repo)
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    title = issue["title"]
    body = issue["body"]
    print(f"issue title: {title}")

    branch = branch_name(ticket_id, branch_slug)
    print(f"creating branch: {branch}")
    try:
        create_branch(branch)
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    write_ticket_md(ticket_id, issue_number, title, body)
    print(f"ticket.md created: runs/{ticket_id}/ticket.md")

    write_state_json(ticket_id, branch, issue_number)
    print(f"state.json initialized: state=INIT branch={branch} issue={issue_number}")

    _log(ticket_id, f"intake: issue=#{issue_number} title={title!r} branch={branch}")
    _log(ticket_id, "intake: done")

    commit_bootstrap(ticket_id, push=push)

    if original_branch and original_branch != branch:
        print(f"returning to original branch: {original_branch}")
        return_to_branch(original_branch)
        _log(ticket_id, f"intake: returned to branch {original_branch!r}")

    print(f"\nrun workflow with:")
    print(
        f"  python tools/agent_runner/run_ticket.py {ticket_id}"
        f" --auto --exec-cmd \"claude --dangerously-skip-permissions -p\""
    )

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform a GitHub Issue into a local ai-dev-factory run"
    )
    parser.add_argument("--issue", type=int, required=True, help="GitHub issue number")
    parser.add_argument("--ticket-id", required=True, help="Ticket id (e.g. T023)")
    parser.add_argument("--branch-slug", required=True, help="Branch suffix after ticket/TXXX-")
    parser.add_argument(
        "--repo", help="GitHub repo (owner/repo) — auto-detected from git remote if omitted"
    )
    parser.add_argument(
        "--push", action="store_true", help="Push branch after bootstrap checkpoint commit"
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return run_intake(args.ticket_id, args.issue, args.branch_slug, args.repo, push=args.push)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
