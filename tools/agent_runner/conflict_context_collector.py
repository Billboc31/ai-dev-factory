#!/usr/bin/env python3
"""Collect conflict context for the conflict resolver agent.

Writes runs/{ticket_id}/conflict/context.md with:
- ticket.md, plan.md, reviews
- PR diff (via gh) — source paths only
- merge-base diff (git diff merge-base..HEAD) — source paths only
- latest main changes since conflict detected
- content of each *source* conflicted file (never foreign runs/ or node_modules)
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

# Keep context.md small enough for GitHub's 100 MB blob limit and for the agent.
_MAX_SECTION_CHARS = 200_000
_MAX_FILE_CHARS = 80_000
_MAX_CONTEXT_CHARS = 1_500_000


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(args: list[str], cwd: str | None = None) -> tuple[str, int]:
    result = subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)
    return result.stdout, result.returncode


def _is_noise_path(path: str, ticket_id: str) -> bool:
    """Paths the conflict agent must never be asked to merge or dump."""
    if not path:
        return True
    if path.startswith("./"):
        path = path[2:]
    if path == "runs" or path.startswith("runs/"):
        # Own ticket runtime artifacts are metadata, not source to merge.
        return True
    if path == "node_modules" or path.startswith("node_modules/"):
        return True
    if "/node_modules/" in path or path.endswith("/node_modules"):
        return True
    parts = path.split("/")
    if "target" in parts or "build" in parts or "dist" in parts:
        return True
    if "__pycache__" in parts or path.endswith((".pyc", ".class")):
        return True
    if path == ".venv" or path.startswith(".venv/") or "/.venv/" in path:
        return True
    if path.endswith((".lock", ".map", ".min.js", ".min.css")):
        return True
    _ = ticket_id
    return False


def _truncate(text: str, limit: int, label: str) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return (
        text[:limit]
        + f"\n\n… truncated {omitted} chars from {label} "
        f"(conflict context size guard) …\n"
    )


def _filter_paths(paths: list[str], ticket_id: str) -> list[str]:
    return [p for p in paths if not _is_noise_path(p, ticket_id)]


def collect_context(
    ticket_id: str,
    conflicted_files: list[str] | None = None,
) -> Path:
    run_dir = Path("runs") / ticket_id
    state_file = run_dir / "state.json"

    data = json.loads(state_file.read_text(encoding="utf-8"))
    conflict_pr_number = data.get("conflict_pr_number")
    # Use caller-supplied list when available (post-rebase real conflicts);
    # fall back to the pre-rebase list stored by the daemon.
    if conflicted_files is None:
        conflicted_files = data.get("conflicted_files") or []
    raw_conflicted = list(conflicted_files)
    conflicted_files = _filter_paths(raw_conflicted, ticket_id)
    skipped = [p for p in raw_conflicted if p not in conflicted_files]
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
        f"- conflicted_files (source): {', '.join(conflicted_files) or 'none'}\n"
        f"- skipped_runtime_noise: {len(skipped)} path(s)"
        + (f" (e.g. {', '.join(skipped[:5])}{'…' if len(skipped) > 5 else ''})" if skipped else "")
    )

    ticket_path = run_dir / "ticket.md"
    if ticket_path.exists():
        sections.append(f"## Ticket\n\n{ticket_path.read_text(encoding='utf-8').strip()}")

    plan_path = run_dir / "plan.md"
    if plan_path.exists():
        sections.append(
            "## Plan\n\n"
            + _truncate(plan_path.read_text(encoding="utf-8").strip(), _MAX_SECTION_CHARS, "plan.md")
        )

    reviews_dir = run_dir / "reviews"
    if reviews_dir.exists():
        review_texts: list[str] = []
        for review in sorted(reviews_dir.glob("*.md")):
            review_texts.append(
                f"### {review.name}\n\n"
                + _truncate(
                    review.read_text(encoding="utf-8").strip(),
                    _MAX_FILE_CHARS,
                    review.name,
                )
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
                f"### {fix.name}\n\n"
                + _truncate(fix.read_text(encoding="utf-8").strip(), _MAX_FILE_CHARS, fix.name)
            )
        if fix_texts:
            sections.append("## Fixes\n\n" + "\n\n".join(fix_texts))

    if conflict_pr_number:
        pr_diff, rc = _run(["gh", "pr", "diff", str(conflict_pr_number)])
        if rc == 0 and pr_diff.strip():
            sections.append(
                f"## PR Diff (PR #{conflict_pr_number})\n\n"
                f"```diff\n{_truncate(pr_diff.strip(), _MAX_SECTION_CHARS, 'pr diff')}\n```"
            )

    # Prefer a path-filtered diff so node_modules / foreign runs never inflate context.
    merge_base_out, rc = _run(["git", "merge-base", "origin/main", "HEAD"])
    if rc == 0 and merge_base_out.strip():
        merge_base = merge_base_out.strip()
        name_only, rc_names = _run(["git", "diff", "--name-only", f"{merge_base}..HEAD"])
        source_paths = _filter_paths(
            [p.strip() for p in name_only.splitlines() if p.strip()],
            ticket_id,
        ) if rc_names == 0 else []
        if source_paths:
            merge_diff, rc2 = _run(["git", "diff", f"{merge_base}..HEAD", "--", *source_paths])
            if rc2 == 0 and merge_diff.strip():
                sections.append(
                    f"## Ticket branch diff since merge-base ({merge_base[:8]})\n\n"
                    f"```diff\n{_truncate(merge_diff.strip(), _MAX_SECTION_CHARS, 'merge-base diff')}\n```"
                )
        else:
            sections.append(
                f"## Ticket branch diff since merge-base ({merge_base[:8]})\n\n"
                "(no source paths — only runtime/noise diffs against main)"
            )

    if conflict_detected_at and conflict_detected_at != "unknown":
        main_log, rc = _run([
            "git", "log", "origin/main", "--oneline",
            f"--since={conflict_detected_at}",
        ])
        if rc == 0 and main_log.strip():
            sections.append(
                f"## Latest main changes since {conflict_detected_at}\n\n"
                f"```\n{_truncate(main_log.strip(), 20_000, 'main log')}\n```"
            )

    if conflicted_files:
        file_sections: list[str] = []
        for f in conflicted_files:
            fp = Path(f)
            if fp.exists():
                content = fp.read_text(encoding="utf-8", errors="replace").strip()
                file_sections.append(
                    f"### {f}\n\n```\n{_truncate(content, _MAX_FILE_CHARS, f)}\n```"
                )
            else:
                file_sections.append(f"### {f}\n\n(file not found in worktree)")
        if file_sections:
            sections.append("## Conflicted Files\n\n" + "\n\n".join(file_sections))
    elif skipped:
        sections.append(
            "## Conflicted Files\n\n"
            "All conflicted paths were runtime/noise "
            f"({len(skipped)} path(s)) — auto-resolved without agent input."
        )

    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    context_path = conflict_dir / "context.md"
    body = "\n\n---\n\n".join(sections)
    context_path.write_text(
        _truncate(body, _MAX_CONTEXT_CHARS, "context.md"),
        encoding="utf-8",
    )
    return context_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: conflict_context_collector.py <ticket_id>", file=sys.stderr)
        sys.exit(2)
    path = collect_context(sys.argv[1])
    print(f"context written to: {path}")
