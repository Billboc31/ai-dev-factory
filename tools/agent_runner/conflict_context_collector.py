#!/usr/bin/env python3
"""Collect conflict context for the conflict resolver agent.

Writes runs/{ticket_id}/conflict/context.md with:
- ticket.md, plan.md, reviews
- PR diff (via gh)
- merge-base diff (git diff merge-base..HEAD)
- latest main changes since conflict detected
- full content of each conflicted file (with conflict markers)
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path


os_environ_copy = None


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(args: list[str], cwd: str | None = None) -> tuple[str, int]:
    result = subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)
    return result.stdout, result.returncode


def collect_context(ticket_id: str) -> Path:
    run_dir = Path("runs") / ticket_id
    state_file = run_dir / "state.json"

    data = json.loads(state_file.read_text(encoding="utf-8"))
    conflict_pr_number = data.get("conflict_pr_number")
    conflicted_files: list[str] = data.get("conflicted_files") or []
    pre_conflict_state = data.get("pre_conflict_state", "unknown")
    conflict_detected_at = data.get("conflict_detected_at", "unknown")

    sections: list[str] = []

    sections.append(
        f"# Conflict Context — {ticket_id}\n\n"
        f"Generated at: {_now_iso()}\n\n"
        f"## Metadata\n\n"
        f"- pre_conflict_state: {pre_conflict_state}\n"
        f"- conflict_detected_at: {conflict_detected_at}\n"
        f"- conflict_pr_number: {conflict_pr_number or 'unknown'}\n"
        f"- conflicted_files: {', '.join(conflicted_files) or 'none'}"
    )

    ticket_path = run_dir / "ticket.md"
    if ticket_path.exists():
        sections.append(f"## Ticket\n\n{ticket_path.read_text(encoding='utf-8').strip()}")

    plan_path = run_dir / "plan.md"
    if plan_path.exists():
        sections.append(f"## Plan\n\n{plan_path.read_text(encoding='utf-8').strip()}")

    reviews_dir = run_dir / "reviews"
    if reviews_dir.exists():
        review_texts: list[str] = []
        for review in sorted(reviews_dir.glob("*.md")):
            review_texts.append(
                f"### {review.name}\n\n{review.read_text(encoding='utf-8').strip()}"
            )
        if review_texts:
            sections.append("## Reviews\n\n" + "\n\n".join(review_texts))

    fixes_dir = run_dir / "fixes"
    if fixes_dir.exists():
        fix_texts: list[str] = []
        for fix in sorted(fixes_dir.glob("*.md")):
            if fix.name.startswith("context-"):
                continue
            fix_texts.append(
                f"### {fix.name}\n\n{fix.read_text(encoding='utf-8').strip()}"
            )
        if fix_texts:
            sections.append("## Fixes\n\n" + "\n\n".join(fix_texts))

    if conflict_pr_number:
        pr_diff, rc = _run(["gh", "pr", "diff", str(conflict_pr_number)])
        if rc == 0 and pr_diff.strip():
            sections.append(
                f"## PR Diff (PR #{conflict_pr_number})\n\n"
                f"```diff\n{pr_diff.strip()}\n```"
            )

    merge_base_out, rc = _run(["git", "merge-base", "origin/main", "HEAD"])
    if rc == 0 and merge_base_out.strip():
        merge_base = merge_base_out.strip()
        merge_diff, rc2 = _run(["git", "diff", f"{merge_base}..HEAD"])
        if rc2 == 0 and merge_diff.strip():
            sections.append(
                f"## Ticket branch diff since merge-base ({merge_base[:8]})\n\n"
                f"```diff\n{merge_diff.strip()}\n```"
            )

    if conflict_detected_at and conflict_detected_at != "unknown":
        main_log, rc = _run([
            "git", "log", "origin/main", "--oneline",
            f"--since={conflict_detected_at}",
        ])
        if rc == 0 and main_log.strip():
            sections.append(
                f"## Latest main changes since {conflict_detected_at}\n\n"
                f"```\n{main_log.strip()}\n```"
            )

    if conflicted_files:
        file_sections: list[str] = []
        for f in conflicted_files:
            fp = Path(f)
            if fp.exists():
                content = fp.read_text(encoding="utf-8", errors="replace").strip()
                file_sections.append(f"### {f}\n\n```\n{content}\n```")
            else:
                file_sections.append(f"### {f}\n\n(file not found in worktree)")
        if file_sections:
            sections.append("## Conflicted Files\n\n" + "\n\n".join(file_sections))

    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    context_path = conflict_dir / "context.md"
    context_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    return context_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: conflict_context_collector.py <ticket_id>", file=sys.stderr)
        sys.exit(2)
    path = collect_context(sys.argv[1])
    print(f"context written to: {path}")
