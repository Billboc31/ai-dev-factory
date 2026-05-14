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
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_STEP = ROOT / "run_step.py"

_spec = importlib.util.spec_from_file_location("_run_step", RUN_STEP)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
validate_planner_output = _mod.validate_planner_output
classify_runtime_failure = _mod.classify_runtime_failure
del _spec, _mod

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

REVIEW_DECISION_KEYWORDS: dict[str, dict[str, str]] = {
    "PLAN_REVIEW_NEEDED": {
        "approve": "PLAN_APPROVED",
        "fix": "PLAN_FIX_REQUIRED",
    },
    "IMPLEMENTATION_REVIEW_NEEDED": {
        "approve": "IMPLEMENTATION_APPROVED",
        "fix": "IMPLEMENTATION_FIX_REQUIRED",
    },
}

# Must stay in sync with run_step.py DEFAULT_OUTPUTS
DEFAULT_OUTPUTS: dict[str, str] = {
    "planner": "plan.md",
    "coder": "implementation-output.md",
    "review": "reviews/review.md",
    "tester": "tests/test-report.md",
}

# Allowed paths for --include-code staging — never extended to "." or "*"
COMMIT_SCOPE: tuple[str, ...] = (
    "tools/",
    "tests/",
    "prompts/",
    "tickets/",
    "docs/",
    "ai/",
)


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
    try:
        _check_working_tree_clean()
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _log_runtime(ticket_id, f"ensure-branch: refused — {exc}")
        return 2
    exists = run_command(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{name}"])
    if exists.returncode == 0:
        _log_runtime(ticket_id, f"ensure-branch: switching to existing branch {name}")
        rc = run_git(["checkout", name])
    else:
        _log_runtime(ticket_id, f"ensure-branch: creating new branch {name}")
        rc = run_git(["checkout", "-b", name])
    if rc == 0:
        _log_runtime(ticket_id, f"ensure-branch: done branch={name}")
    else:
        _log_runtime(ticket_id, f"ensure-branch: failed branch={name}")
    return rc


def _warn_out_of_scope(ticket_id: str, run_dir: str) -> None:
    """Print and log files modified outside run_dir and COMMIT_SCOPE — never stages them."""
    allowed = (run_dir,) + COMMIT_SCOPE
    result = run_command(["git", "status", "--porcelain"])
    if result.returncode != 0:
        return
    out_of_scope = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if not any(path.startswith(prefix) for prefix in allowed):
            out_of_scope.append(path)
    if out_of_scope:
        print(f"warning: {len(out_of_scope)} file(s) modified outside commit scope — not staged:")
        for p in out_of_scope:
            print(f"  {p}")
        _log_runtime(ticket_id, f"commit-checkpoint: out-of-scope skipped: {out_of_scope!r}")


def commit_ticket(ticket_id: str, message: str | None, include_code: bool = False) -> int:
    # Validate branch against state.json before touching anything
    try:
        state = load_state(ticket_id)
        current_state = state.get("state", "unknown")
        expected_branch = state.get("branch")
    except TicketRunnerError:
        current_state = "unknown"
        expected_branch = None

    if expected_branch:
        try:
            current_branch = _get_current_branch()
        except TicketRunnerError as exc:
            print(f"error: {exc}", file=sys.stderr)
            _log_runtime(ticket_id, f"commit-checkpoint: refused — {exc}")
            return 2
        if current_branch != expected_branch:
            msg = f"current branch '{current_branch}' does not match state branch '{expected_branch}'"
            print(f"error: {msg}", file=sys.stderr)
            _log_runtime(ticket_id, f"commit-checkpoint: refused — {msg}")
            return 2

    run_dir = f"runs/{ticket_id}/"
    stage_paths = [run_dir] + (list(COMMIT_SCOPE) if include_code else [])

    status_result = run_command(["git", "status", "--porcelain"] + stage_paths)
    if status_result.returncode != 0:
        print("error: failed to check git status", file=sys.stderr)
        _log_runtime(ticket_id, "commit-checkpoint: failed to check git status")
        return 2
    if not status_result.stdout.strip():
        print(
            "nothing to commit in runs/ artifacts — stage other changes manually or check status",
            file=sys.stderr,
        )
        _log_runtime(ticket_id, "commit-checkpoint: refused — nothing to commit in runs/")
        return 1

    if message is None:
        message = f"{ticket_id}: checkpoint [{current_state}] — update workflow artifacts"

    if include_code:
        _warn_out_of_scope(ticket_id, run_dir)

    print(f"staging: {run_dir}")
    if include_code:
        print(f"staging (include-code): {', '.join(COMMIT_SCOPE)}")
        print("note: staging runs/ and allowed scope paths — never git add .")
    else:
        print("note: only runs/ artifacts are auto-staged — stage other changes manually before running --commit")

    for path in stage_paths:
        add_result = run_command(["git", "add", path])
        print_result(add_result)
        if add_result.returncode != 0:
            _log_runtime(ticket_id, f"commit-checkpoint: failed to stage {path}")
            return add_result.returncode

    commit_result = run_command(["git", "commit", "-m", message])
    rc = print_result(commit_result)
    if rc == 0:
        sha_result = run_command(["git", "rev-parse", "--short", "HEAD"])
        sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown"
        _log_runtime(ticket_id, f"commit-checkpoint: sha={sha} message={message!r}")
    else:
        _log_runtime(ticket_id, "commit-checkpoint: failed")
    return rc


def push_branch(ticket_id: str, slug: str | None) -> int:
    try:
        state = load_state(ticket_id)
        expected_branch = state.get("branch")
    except TicketRunnerError:
        print("warning: state.json not found — skipping branch verification", file=sys.stderr)
        _log_runtime(ticket_id, "push: warning — state.json absent, branch not verified")
        expected_branch = None

    if expected_branch:
        try:
            current_branch = _get_current_branch()
        except TicketRunnerError as exc:
            print(f"error: {exc}", file=sys.stderr)
            _log_runtime(ticket_id, f"push: refused — {exc}")
            return 2
        if current_branch != expected_branch:
            msg = f"current branch '{current_branch}' does not match state branch '{expected_branch}'"
            print(f"error: {msg}", file=sys.stderr)
            _log_runtime(ticket_id, f"push: refused — {msg}")
            return 2
        push_target = expected_branch
    else:
        push_target = branch_name(ticket_id, slug)

    # Non-blocking warning if working tree is dirty
    wt_result = run_command(["git", "status", "--porcelain"])
    if wt_result.returncode == 0 and wt_result.stdout.strip():
        print("warning: working tree has uncommitted changes — push proceeds", file=sys.stderr)
        _log_runtime(ticket_id, "push: warning — working tree dirty")

    print(f"push branch: {push_target}")
    _log_runtime(ticket_id, f"push: pushing branch={push_target}")
    rc = run_git(["push", "-u", "origin", push_target])
    if rc == 0:
        _log_runtime(ticket_id, f"push: done branch={push_target}")
    else:
        _log_runtime(ticket_id, f"push: failed branch={push_target}")
    return rc


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
            "working tree is not clean — commit or stash changes first"
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


def _review_output_rel(current_state: str) -> str:
    if current_state == "PLAN_REVIEW_NEEDED":
        return "reviews/plan-review.md"
    if current_state == "IMPLEMENTATION_REVIEW_NEEDED":
        return "reviews/implementation-review.md"
    return DEFAULT_OUTPUTS["review"]


def _call_run_step(
    ticket_id: str,
    step: str,
    exec_cmd: str,
    extra_context_file: Path | None = None,
    current_state: str | None = None,
) -> tuple[int, str, Path]:
    """Invoke run_step.py for one step; return (exit_code, output_file_content, output_path)."""
    if step == "review" and current_state is not None:
        output_rel = _review_output_rel(current_state)
    else:
        output_rel = DEFAULT_OUTPUTS.get(step, f"{step}-output.md")

    output_path = Path("runs") / ticket_id / output_rel

    cmd = [
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        step,
        "--exec-cmd",
        exec_cmd,
        "--output-path",
        str(output_path),
    ]
    if extra_context_file is not None:
        cmd += ["--extra-context-file", str(extra_context_file)]
    result = run_command(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if output_path.exists():
        output_content = output_path.read_text(encoding="utf-8")
    else:
        output_content = ""
        if result.returncode == 0:
            print(f"warning: expected output file {output_path} not found", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: output file missing: {output_path}")

    if result.returncode != 0:
        failure_class = classify_runtime_failure(result.returncode, output_content, result.stderr)
        _log_runtime(ticket_id, f"auto-run: runtime failure: {failure_class} (rc={result.returncode})")

    return result.returncode, output_content, output_path


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


def _build_review_decision_context_file(ticket_id: str, current_state: str) -> Path:
    """Write review decision keywords to a reviewable artifact; return its path."""
    keywords = REVIEW_DECISION_KEYWORDS[current_state]
    context_path = Path("runs") / ticket_id / "reviews" / f"review-decision-context-{current_state}.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "## Review decision keywords\n\n"
        "The review must end with exactly one valid workflow keyword on its own line.\n\n"
        f"Approval keyword:\n{keywords['approve']}\n\n"
        f"Fix required keyword:\n{keywords['fix']}\n"
    )
    context_path.write_text(content, encoding="utf-8")
    return context_path


def _append_workflow_journal(ticket_id: str, prev_state: str, step: str, next_state: str) -> None:
    run_dir = Path("runs") / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "workflow-status.md"
    entry = f"\n## {_now_iso()}\n\n- prev: {prev_state}\n- step: {step}\n- next: {next_state}\n"
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ── human approval ───────────────────────────────────────────────────────────

# Maps CLI command name → (required_current_state, target_state)
HUMAN_APPROVAL_TRANSITIONS: dict[str, tuple[str, str]] = {
    "approve-plan":               ("PLAN_REVIEW_NEEDED",           "PLAN_APPROVED"),
    "request-plan-fix":           ("PLAN_REVIEW_NEEDED",           "PLAN_FIX_REQUIRED"),
    "approve-implementation":     ("IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_APPROVED"),
    "request-implementation-fix": ("IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_FIX_REQUIRED"),
}


def apply_human_approval(ticket_id: str, command: str) -> int:
    required_state, target_state = HUMAN_APPROVAL_TRANSITIONS[command]
    try:
        state = load_state(ticket_id)
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    current_state = state["state"]
    if current_state != required_state:
        print(
            f"error: --{command} requires state {required_state!r}, current state is {current_state!r}",
            file=sys.stderr,
        )
        _log_runtime(ticket_id, f"human-approval: refused {command!r} — expected {required_state!r}, got {current_state!r}")
        return 2
    save_state(ticket_id, {**state, "state": target_state})
    _append_workflow_journal(ticket_id, current_state, command, target_state)
    _log_runtime(ticket_id, f"human-approval: {command} — {current_state} → {target_state}")
    print(f"approved: {current_state} → {target_state}")
    return 0


# ── --set-state ───────────────────────────────────────────────────────────────

def set_workflow_state(ticket_id: str, new_state: str) -> int:
    if new_state not in VALID_STATES:
        allowed = ", ".join(sorted(VALID_STATES))
        print(f"error: unknown state {new_state!r}. Allowed: {allowed}", file=sys.stderr)
        return 2
    try:
        state = load_state(ticket_id)
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    old_state = state["state"]
    save_state(ticket_id, {**state, "state": new_state})
    _log_runtime(ticket_id, f"set-state: {old_state} → {new_state} (human)")
    print(f"state updated: {old_state} → {new_state}")
    return 0


# ── --ticket-source ───────────────────────────────────────────────────────────

def _copy_ticket_source(ticket_id: str, source: str) -> None:
    """Copy a local ticket file to runs/TXXX/ticket.md.

    Raises TicketRunnerError on path traversal, missing file, or directory.
    """
    if ".." in Path(source).parts:
        raise TicketRunnerError(f"ticket-source path must not contain '..': {source!r}")
    src = Path(source)
    if not src.exists():
        raise TicketRunnerError(f"ticket-source not found: {source!r}")
    if src.is_dir():
        raise TicketRunnerError(f"ticket-source must be a file, not a directory: {source!r}")
    dest = Path("runs") / ticket_id / "ticket.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    _log_runtime(ticket_id, f"ticket-source: copied {source!r} → {dest}")


# ── --auto-init ───────────────────────────────────────────────────────────────

def init_auto(ticket_id: str, branch_slug: str | None, ticket_source: str | None = None) -> int:
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

    if ticket_source:
        try:
            _copy_ticket_source(ticket_id, ticket_source)
            print(f"ticket source snapshot created: runs/{ticket_id}/ticket.md")
        except TicketRunnerError as exc:
            print(f"error: {exc}", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-init: ticket-source failed: {exc}")
            return 2

    return 0


# ── --auto ────────────────────────────────────────────────────────────────────

def auto_run(ticket_id: str, exec_cmd: str, auto_commit: bool = False, auto_push: bool = False) -> int:
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

    if step == "review" and current_state in REVIEW_DECISION_KEYWORDS:
        extra_context_file = _build_review_decision_context_file(ticket_id, current_state)
        _log_runtime(ticket_id, f"auto-run: review decision context: context_file={extra_context_file}")

    rc, output_content, output_path = _call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state)
    _log_runtime(ticket_id, f"auto-run: step={step} done rc={rc}")

    if rc != 0:
        failure_class = classify_runtime_failure(rc, output_content, "")
        _log_runtime(ticket_id, f"auto-run: runtime failure: {failure_class} (rc={rc})")
        print(f"error: step '{step}' exited with code {rc} — state unchanged ({current_state})", file=sys.stderr)
        _log_runtime(ticket_id, f"auto-run: step={step} failed rc={rc}, state unchanged={current_state}")
        return 2

    if step == "planner":
        reasons = validate_planner_output(output_content)
        if reasons:
            for reason in reasons:
                _log_runtime(ticket_id, f"planner validation failed: {reason}")
                print(f"error: planner output invalid: {reason}", file=sys.stderr)
            _log_runtime(ticket_id, "planner validation: rejected — state unchanged")
            return 2
        _log_runtime(ticket_id, "planner validation success")

    if not is_deterministic:
        _log_runtime(ticket_id, f"auto-run: review parsed from: {output_path}")

    next_state = _determine_next_state(is_deterministic, output_content, possible_next)

    if next_state is None:
        print(
            f"warning: no review keyword found in output of step '{step}' — state unchanged ({current_state})",
            file=sys.stderr,
        )
        _log_runtime(ticket_id, f"auto-run: no keyword found in {output_path}")
        return 1

    if not is_deterministic:
        _log_runtime(ticket_id, f"auto-run: keyword detected: {next_state}")

    save_state(ticket_id, {**state, "state": next_state})
    _append_workflow_journal(ticket_id, current_state, step, next_state)
    _log_runtime(ticket_id, f"auto-run: transition {current_state} → {next_state}")
    print(f"[auto] {current_state} → {next_state}")

    if auto_commit:
        _log_runtime(ticket_id, "auto-run: auto-commit triggered")
        commit_rc = commit_ticket(ticket_id, None)
        if commit_rc == 0 and auto_push:
            _log_runtime(ticket_id, "auto-run: auto-push triggered")
            push_rc = push_branch(ticket_id, None)
            if push_rc != 0:
                print(f"warning: auto-push failed (rc={push_rc}) — state saved", file=sys.stderr)
                _log_runtime(ticket_id, f"auto-run: auto-push failed rc={push_rc}")
        elif commit_rc not in (0, 1):
            print(f"warning: auto-commit failed (rc={commit_rc}) — state saved, push skipped", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: auto-commit failed rc={commit_rc}")

    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sequential ai-dev-factory ticket runner")
    parser.add_argument("ticket_id")
    parser.add_argument("--once", help="Execute a single explicit step")
    parser.add_argument("--exec-cmd", help="External command to execute")
    parser.add_argument("--branch", action="store_true", help="Create or switch to the ticket branch (with working-tree guard)")
    parser.add_argument("--ensure-branch", action="store_true", help="Alias for --branch")
    parser.add_argument("--branch-slug", help="Branch suffix after TXXX")
    parser.add_argument("--commit", action="store_true", help="Commit runs/ artifacts as a checkpoint")
    parser.add_argument("--commit-message", help="Custom commit message")
    parser.add_argument("--include-code", action="store_true", help="With --commit, also stage COMMIT_SCOPE paths (tools/, tests/, prompts/, tickets/, docs/, ai/)")
    parser.add_argument("--push", action="store_true", help="Push the ticket branch (verified against state.json)")
    parser.add_argument("--auto", action="store_true", help="Execute next workflow step (reads state.json)")
    parser.add_argument("--auto-init", action="store_true", help="Initialize state.json for --auto mode")
    parser.add_argument("--ticket-source", help="Path to local ticket file to snapshot into runs/TXXX/ticket.md (use with --auto-init)")
    parser.add_argument("--auto-commit", action="store_true", help="After each successful --auto step, commit runs/ artifacts")
    parser.add_argument("--auto-push", action="store_true", help="After each successful --auto-commit, push the ticket branch")
    parser.add_argument("--set-state", help="Manually set workflow state (human review path)")
    parser.add_argument("--approve-plan", action="store_true", help="Approve plan (PLAN_REVIEW_NEEDED → PLAN_APPROVED)")
    parser.add_argument("--request-plan-fix", action="store_true", help="Request plan fix (PLAN_REVIEW_NEEDED → PLAN_FIX_REQUIRED)")
    parser.add_argument("--approve-implementation", action="store_true", help="Approve implementation (IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_APPROVED)")
    parser.add_argument("--request-implementation-fix", action="store_true", help="Request implementation fix (IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_FIX_REQUIRED)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        ticket_id = validate_ticket_id(args.ticket_id)

        if args.set_state:
            return set_workflow_state(ticket_id, args.set_state)

        for cmd, attr in (
            ("approve-plan",               "approve_plan"),
            ("request-plan-fix",           "request_plan_fix"),
            ("approve-implementation",     "approve_implementation"),
            ("request-implementation-fix", "request_implementation_fix"),
        ):
            if getattr(args, attr):
                return apply_human_approval(ticket_id, cmd)

        if args.auto_init:
            return init_auto(ticket_id, args.branch_slug, getattr(args, "ticket_source", None))

        if args.branch or args.ensure_branch:
            return checkout_branch(ticket_id, args.branch_slug)

        if args.commit:
            return commit_ticket(ticket_id, args.commit_message, include_code=args.include_code)

        if args.push:
            return push_branch(ticket_id, args.branch_slug)

        if args.auto:
            if not args.exec_cmd:
                print("error: --exec-cmd is required with --auto", file=sys.stderr)
                return 2
            return auto_run(ticket_id, args.exec_cmd, auto_commit=args.auto_commit, auto_push=args.auto_push)

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
