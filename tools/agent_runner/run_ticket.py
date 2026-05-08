#!/usr/bin/env python3
"""Sequential ticket runner for ai-dev-factory.

This runner remains intentionally explicit:
- no autonomous merge
- no hidden network calls except explicit git commands
- no prompt generation
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_STEP = ROOT / "run_step.py"

VALID_STATES = frozenset({
    "INIT",
    "PLAN_REVIEW_NEEDED",
    "PLAN_FIX_REQUIRED",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_FIX_REQUIRED",
    "IMPLEMENTATION_APPROVED",
    "TEST_COMPLETE",
})

# Maps state -> (step, is_deterministic, possible_next_states_in_order)
# None marks a terminal state with no further transitions.
TRANSITIONS: dict[str, tuple[str, bool, list[str]] | None] = {
    "INIT":                         ("planner", True,  ["PLAN_REVIEW_NEEDED"]),
    "PLAN_REVIEW_NEEDED":           ("review",  False, ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]),
    "PLAN_FIX_REQUIRED":            ("planner", True,  ["PLAN_REVIEW_NEEDED"]),
    "PLAN_APPROVED":                ("coder",   True,  ["IMPLEMENTATION_REVIEW_NEEDED"]),
    "IMPLEMENTATION_REVIEW_NEEDED": ("review",  False, ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]),
    "IMPLEMENTATION_FIX_REQUIRED":  ("coder",   True,  ["IMPLEMENTATION_REVIEW_NEEDED"]),
    "IMPLEMENTATION_APPROVED":      ("tester",  True,  ["TEST_COMPLETE"]),
    "TEST_COMPLETE":                None,
}

# Must stay in sync with run_step.py DEFAULT_OUTPUTS
DEFAULT_OUTPUTS: dict[str, str] = {
    "planner": "plan.md",
    "coder": "implementation-output.md",
    "review": "reviews/review.md",
    "tester": "tests/test-report.md",
}


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


# ── state machine helpers ─────────────────────────────────────────────────────

def _state_path(ticket_id: str) -> Path:
    return Path("runs") / ticket_id / "state.json"


def _runtime_log_path(ticket_id: str) -> Path:
    return Path("runs") / ticket_id / "runtime.log"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_runtime(ticket_id: str, message: str) -> None:
    log_path = _runtime_log_path(ticket_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] {message}\n")


def load_state(ticket_id: str) -> dict:
    path = _state_path(ticket_id)
    if not path.exists():
        raise TicketRunnerError("state.json not found — run --auto-init first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise TicketRunnerError("state.json is corrupted")
    state_value = data.get("state")
    if not state_value or state_value not in VALID_STATES:
        raise TicketRunnerError(f"unknown state: {state_value!r}")
    return data


def save_state(ticket_id: str, state_dict: dict) -> None:
    path = _state_path(ticket_id)
    updated = {**state_dict, "updated_at": _now_iso()}
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    tmp.rename(path)  # atomic on same filesystem


def _get_current_branch() -> str:
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        raise TicketRunnerError("failed to determine current git branch")
    return result.stdout.strip()


def _check_working_tree_clean() -> None:
    result = run_command(["git", "status", "--porcelain"])
    if result.returncode != 0:
        raise TicketRunnerError("failed to check git status")
    if result.stdout.strip():
        raise TicketRunnerError(
            "working tree is not clean — commit or stash changes before running --auto"
        )


def _determine_next_state(
    is_deterministic: bool,
    output: str,
    possible_next: list[str],
) -> str | None:
    if is_deterministic:
        return possible_next[0]
    found = [kw for kw in possible_next if re.search(rf"^{re.escape(kw)}$", output, re.MULTILINE)]
    if not found:
        return None
    if len(found) > 1:
        print(
            f"warning: multiple review keywords found {found!r} — using first: {found[0]!r}",
            file=sys.stderr,
        )
    return found[0]


def _call_run_step(ticket_id: str, step: str, exec_cmd: str, extra_context_file: Path | None = None) -> tuple[int, str]:
    """Invoke run_step.py for one step; return (exit_code, output_file_content)."""
    cmd = [
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        step,
        "--exec-cmd",
        exec_cmd,
    ]
    if extra_context_file is not None:
        cmd += ["--extra-context-file", str(extra_context_file)]
    result = run_command(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    output_rel = DEFAULT_OUTPUTS.get(step, f"{step}-output.md")
    output_path = Path("runs") / ticket_id / output_rel
    if output_path.exists():
        output_content = output_path.read_text(encoding="utf-8")
    else:
        output_content = ""
        if result.returncode == 0:
            print(f"warning: expected output file {output_path} not found", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: output file missing: {output_path}")
    return result.returncode, output_content


def _collect_fix_artifacts(ticket_id: str, state: dict) -> dict:
    """Return paths for previous_output, review, fix_instructions for the current fix state.

    Raises TicketRunnerError with the expected path if any artifact is missing.
    """
    current_state = state["state"]
    run_dir = Path("runs") / ticket_id

    if current_state == "PLAN_FIX_REQUIRED":
        previous_output_rel = DEFAULT_OUTPUTS["planner"]
        review_glob = "reviews/plan-review*.md"
        fix_glob = "fixes/plan-fix-*.md"
    else:  # IMPLEMENTATION_FIX_REQUIRED
        previous_output_rel = DEFAULT_OUTPUTS["coder"]
        review_glob = "reviews/implementation-review*.md"
        fix_glob = "fixes/implementation-fix-*.md"

    previous_output = run_dir / previous_output_rel
    if not previous_output.exists():
        raise TicketRunnerError(f"fix artifact missing: {previous_output}")

    review_candidates = sorted(run_dir.glob(review_glob), key=lambda p: p.stat().st_mtime)
    if not review_candidates:
        raise TicketRunnerError(f"fix artifact missing: no file matching {run_dir / review_glob}")
    review = review_candidates[-1]

    fix_candidates = [
        p for p in sorted(run_dir.glob(fix_glob), key=lambda p: p.stat().st_mtime)
        if not p.name.startswith("context-")
    ]
    if not fix_candidates:
        raise TicketRunnerError(f"fix artifact missing: no file matching {run_dir / fix_glob}")
    fix_instructions = fix_candidates[-1]

    return {
        "previous_output": previous_output,
        "review": review,
        "fix_instructions": fix_instructions,
    }


def _build_fix_context_file(ticket_id: str, artifacts: dict) -> Path:
    """Concatenate fix artifacts into a timestamped context file; return its path."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_path = Path("runs") / ticket_id / "fixes" / f"context-{ts}.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    for key, label in [
        ("previous_output", "## Output précédent"),
        ("review", "## Review"),
        ("fix_instructions", "## Instructions de fix"),
    ]:
        content = artifacts[key].read_text(encoding="utf-8")
        sections.append(f"{label}\n\n{content.strip()}")

    context_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    return context_path


def _append_workflow_journal(ticket_id: str, prev_state: str, step: str, next_state: str) -> None:
    run_dir = Path("runs") / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "workflow-status.md"
    entry = f"\n## {_now_iso()}\n\n- prev: {prev_state}\n- step: {step}\n- next: {next_state}\n"
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ── --auto-init ───────────────────────────────────────────────────────────────

def init_auto(ticket_id: str, branch_slug: str | None) -> int:
    if not branch_slug:
        print("error: --branch-slug is required with --auto-init", file=sys.stderr)
        return 2

    try:
        current_branch = _get_current_branch()
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    expected = branch_name(ticket_id, branch_slug)
    if current_branch != expected:
        print(
            f"error: current branch '{current_branch}' does not match expected '{expected}'",
            file=sys.stderr,
        )
        return 2

    path = _state_path(ticket_id)
    if path.exists():
        print(
            f"error: state.json already exists at {path} — delete it first to re-initialize",
            file=sys.stderr,
        )
        return 2

    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "ticket_id": ticket_id,
        "state": "INIT",
        "branch": current_branch,
        "updated_at": _now_iso(),
    }
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"initialized state.json for {ticket_id}: state=INIT branch={current_branch}")
    _log_runtime(ticket_id, f"auto-init: state=INIT branch={current_branch}")
    return 0


# ── --auto ────────────────────────────────────────────────────────────────────

def auto_run(ticket_id: str, exec_cmd: str) -> int:
    try:
        state = load_state(ticket_id)
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    current_state = state["state"]
    _log_runtime(ticket_id, f"auto-run start: state={current_state}")

    # Gate 3: terminal state
    if current_state == "TEST_COMPLETE":
        print("workflow complete — no automatic merge")
        _log_runtime(ticket_id, "auto-run: workflow complete (TEST_COMPLETE)")
        return 0

    # Gate 4: branch matches; Gate 5: working tree clean
    try:
        current_branch = _get_current_branch()
        if current_branch != state["branch"]:
            raise TicketRunnerError(
                f"current branch '{current_branch}' does not match state branch '{state['branch']}'"
            )
        _check_working_tree_clean()
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _log_runtime(ticket_id, f"auto-run gate failed: {exc}")
        return 2

    transition = TRANSITIONS[current_state]
    if transition is None:
        # Unreachable after TEST_COMPLETE guard above, but kept for safety
        print("workflow complete — no automatic merge")
        return 0

    step, is_deterministic, possible_next = transition
    print(f"[auto] state={current_state} step={step}")
    _log_runtime(ticket_id, f"auto-run: running step={step}")

    extra_context_file: Path | None = None
    if current_state in {"PLAN_FIX_REQUIRED", "IMPLEMENTATION_FIX_REQUIRED"}:
        try:
            artifacts = _collect_fix_artifacts(ticket_id, state)
        except TicketRunnerError as exc:
            print(f"error: {exc}", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: {exc}")
            return 2
        extra_context_file = _build_fix_context_file(ticket_id, artifacts)
        for key, path in artifacts.items():
            _log_runtime(ticket_id, f"auto-run: fix context: {key}={path}")
        _log_runtime(ticket_id, f"auto-run: fix context: context_file={extra_context_file}")

    rc, output_content = _call_run_step(ticket_id, step, exec_cmd, extra_context_file)
    _log_runtime(ticket_id, f"auto-run: step={step} done rc={rc}")

    if rc != 0:
        print(f"error: step '{step}' exited with code {rc} — state unchanged ({current_state})", file=sys.stderr)
        _log_runtime(ticket_id, f"auto-run: step={step} failed rc={rc}, state unchanged={current_state}")
        return 2

    next_state = _determine_next_state(is_deterministic, output_content, possible_next)

    if next_state is None:
        print(
            f"warning: no review keyword found in output of step '{step}' — state unchanged ({current_state})",
            file=sys.stderr,
        )
        _log_runtime(ticket_id, f"auto-run: no keyword found, state unchanged={current_state}")
        return 1

    save_state(ticket_id, {**state, "state": next_state})
    _append_workflow_journal(ticket_id, current_state, step, next_state)
    _log_runtime(ticket_id, f"auto-run: transition {current_state} → {next_state}")
    print(f"[auto] {current_state} → {next_state}")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

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
    parser.add_argument("--auto", action="store_true", help="Execute next workflow step (reads state.json)")
    parser.add_argument("--auto-init", action="store_true", help="Initialize state.json for --auto mode")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        ticket_id = validate_ticket_id(args.ticket_id)

        if args.auto_init:
            return init_auto(ticket_id, args.branch_slug)

        if args.branch:
            return checkout_branch(ticket_id, args.branch_slug)

        if args.commit:
            return commit_ticket(ticket_id, args.commit_message)

        if args.push:
            return push_branch(ticket_id, args.branch_slug)

        if args.auto:
            if not args.exec_cmd:
                print("error: --exec-cmd is required with --auto", file=sys.stderr)
                return 2
            return auto_run(ticket_id, args.exec_cmd)

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
