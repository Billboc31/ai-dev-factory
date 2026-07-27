#!/usr/bin/env python3
"""Sequential ticket runner for ai-dev-factory.

This runner orchestrates the ticket workflow explicitly. At ``TEST_COMPLETE`` it
runs the shared PR lifecycle (create PR, auto-merge, close issue) via
``ticket_pr_lifecycle``.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path


# Worker processes must not leave .pyc files behind in the worktree —
# they pollute the working tree between steps and would otherwise show up
# as dirty between commit and push.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parent
RUN_STEP = ROOT / "run_step.py"
RUNTIME_CHECKPOINT = ROOT / "runtime_checkpoint.py"

_spec = importlib.util.spec_from_file_location("_run_step", RUN_STEP)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
validate_planner_output = _mod.validate_planner_output
classify_runtime_failure = _mod.classify_runtime_failure
META_REPORT_REASON = _mod.META_REPORT_REASON
del _spec, _mod

_rc_spec = importlib.util.spec_from_file_location("_runtime_checkpoint", RUNTIME_CHECKPOINT)
_rc_mod = importlib.util.module_from_spec(_rc_spec)  # type: ignore[arg-type]
_rc_spec.loader.exec_module(_rc_mod)  # type: ignore[union-attr]
classify_intake_dirty_paths = _rc_mod.classify_intake_dirty_paths
parse_porcelain_paths = _rc_mod.parse_porcelain_paths
is_runtime_ignored_path = _rc_mod.is_runtime_ignored_path
checkpoint_transition = _rc_mod.checkpoint_transition
CheckpointError = _rc_mod.CheckpointError
DirtyTreeError = _rc_mod.DirtyTreeError
del _rc_spec, _rc_mod

VALID_STATES = frozenset({
    "INIT",
    "PLAN_REVIEW_NEEDED",
    "PLAN_FIX_REQUIRED",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_FIX_REQUIRED",
    "IMPLEMENTATION_APPROVED",
    "TEST_COMPLETE",
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})

# Maps state -> (step, is_deterministic, possible_next_states_in_order)
# None marks a terminal state with no further transitions.
# Conflict states are not auto-runnable; they are managed via API/CLI only.
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
    "services/",
    "runs/",
    "apps/",
    "backend/",
    "frontend/",
    "README.md",
    ".gitignore",
    "package.json",
    "package-lock.json",
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


def run_command(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    # Force PYTHONDONTWRITEBYTECODE=1 for any subprocess we spawn so we never
    # leak .pyc files into the worktree mid-step (the run_step.py invocation
    # below would otherwise import the agent_runner package and write its
    # cache files into the worker's worktree).
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
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


def execute_once(ticket_id: str, step: str, command: str, project_root: Path | None = None) -> int:
    cmd = [sys.executable, str(RUN_STEP), ticket_id, step, "--exec-cmd", command]
    if project_root is not None:
        cmd += ["--project-root", str(project_root)]
    result = run_command(cmd)
    return print_result(result)


def checkout_branch(ticket_id: str, slug: str | None) -> int:
    name = branch_name(ticket_id, slug)
    try:
        current = _get_current_branch()
    except TicketRunnerError:
        current = None
    if current == name:
        print(f"already on branch: {name}")
        _log_runtime(ticket_id, f"ensure-branch: already on branch {name}")
        return 0
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


def _staged_paths() -> list[str]:
    """Return the list of paths currently staged for commit."""
    res = run_command(["git", "diff", "--cached", "--name-only"])
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def _unstage_runtime_garbage(ticket_id: str) -> list[str]:
    """Unstage any runtime-ignored path that ``git add -A`` may have picked up.

    Returns the list of paths that were unstaged so the caller can log them.
    """
    unstaged: list[str] = []
    for path in _staged_paths():
        if is_runtime_ignored_path(path):
            reset = run_command(["git", "reset", "HEAD", "--", path])
            if reset.returncode == 0:
                unstaged.append(path)
            else:
                _log_runtime(
                    ticket_id,
                    f"commit-checkpoint: failed to unstage runtime path {path!r}: "
                    f"{reset.stderr.strip()}",
                )
    return unstaged


def _stage_useful_changes(ticket_id: str, include_code: bool) -> tuple[list[str], list[str]]:
    """Stage all useful changes for the auto-commit.

    Strategy (when ``include_code`` is True — the typical autonomous flow):

    1. ``git add -A`` to pick up code, tests, prompts, docs, dashboard, API,
       workflow artifacts, *and* anything else the worker may legitimately
       have touched outside the predefined COMMIT_SCOPE.
    2. Unstage any path that :func:`is_runtime_ignored_path` classifies as
       runtime garbage (logs, locks, caches, SQLite live DB, etc.).
    3. Return ``(useful, dropped)`` where ``useful`` is the list of paths
       remaining in the index and ``dropped`` is the list of runtime paths
       that were filtered out.

    When ``include_code`` is False the historical narrow behaviour is kept:
    only ``runs/<ticket>/`` is staged. This path is still used by tooling
    that explicitly does not want to ship code in a checkpoint commit.
    """
    run_dir = f"runs/{ticket_id}/"
    dropped: list[str] = []

    if include_code:
        add_result = run_command(["git", "add", "-A"])
        if add_result.returncode != 0:
            _log_runtime(
                ticket_id,
                f"commit-checkpoint: git add -A failed: {add_result.stderr.strip()}",
            )
            return [], []
        dropped = _unstage_runtime_garbage(ticket_id)
        if dropped:
            print(f"unstaged runtime garbage ({len(dropped)}): {', '.join(dropped)}")
            _log_runtime(
                ticket_id,
                f"commit-checkpoint: unstaged runtime garbage: {dropped!r}",
            )
        return _staged_paths(), dropped

    if not Path(run_dir).exists():
        return [], []
    add_result = run_command(["git", "add", run_dir])
    if add_result.returncode != 0:
        _log_runtime(
            ticket_id,
            f"commit-checkpoint: git add {run_dir} failed: {add_result.stderr.strip()}",
        )
        return [], []
    # Drop runtime garbage even from the narrow scope (runs/<ticket>/runtime.log)
    dropped = _unstage_runtime_garbage(ticket_id)
    return _staged_paths(), dropped


def _infer_commit_type(step: str | None, staged: list[str]) -> str:
    """Conventional-commit type derived from the workflow step and staged paths."""
    if step == "planner":
        return "docs"
    if step == "review":
        return "chore"
    if step == "tester":
        return "test"
    # coder, fix, manual checkpoint: classify by content
    if any(p.startswith(("tests/", "runs/")) and p.endswith(".py") for p in staged):
        pass  # fall through
    if all(p.startswith("runs/") for p in staged) and staged:
        return "chore"
    return "feat"


def _summarize_scope(staged: list[str], ticket_id: str) -> str:
    """Short human label of *which* parts of the repo changed."""
    scopes: list[str] = []
    seen: set[str] = set()
    def _add(label: str) -> None:
        if label not in seen:
            seen.add(label)
            scopes.append(label)

    for p in staged:
        if p.startswith("apps/") or "dashboard" in p:
            _add("dashboard")
        elif p.startswith("services/control_api"):
            _add("control-api")
        elif p.startswith("services/"):
            _add("services")
        elif p.startswith("tools/agent_runner"):
            _add("runtime")
        elif p.startswith("tools/"):
            _add("tools")
        elif p.startswith("tests/"):
            _add("tests")
        elif p.startswith("prompts/"):
            _add("prompts")
        elif p.startswith("docs/") or p.startswith("ai/"):
            _add("docs")
        elif p.startswith(f"runs/{ticket_id}/"):
            _add("workflow")
    if not scopes:
        return "workflow"
    return ",".join(scopes[:3])


def _build_commit_message(
    ticket_id: str,
    workflow_step: str | None,
    workflow_state: str,
    staged: list[str],
) -> str:
    """Generate a conventional commit message from runtime context.

    Falls back to a generic checkpoint message if no staged files are
    available. The body lists up to ten staged files and always closes with
    ``refs <ticket_id>`` so the commit is traceable to its ticket.
    """
    if not staged:
        return f"chore({ticket_id}): checkpoint [{workflow_state}]"

    commit_type = _infer_commit_type(workflow_step, staged)
    scope = _summarize_scope(staged, ticket_id)
    step_label = workflow_step or workflow_state.lower()

    title = f"{commit_type}({ticket_id}/{scope}): {step_label} — update {len(staged)} file(s)"

    body_lines = [f"workflow step: {step_label}", f"state: {workflow_state}", ""]
    body_lines.append("Files:")
    for p in staged[:10]:
        body_lines.append(f"- {p}")
    if len(staged) > 10:
        body_lines.append(f"- … and {len(staged) - 10} more")
    body_lines += ["", f"refs {ticket_id}"]

    return title + "\n\n" + "\n".join(body_lines)


def commit_ticket(
    ticket_id: str,
    message: str | None,
    include_code: bool = False,
    workflow_step: str | None = None,
) -> int:
    """Commit useful changes for ``ticket_id``.

    Strategy:
      1. Verify the current branch matches state.json.
      2. Stage useful changes (``_stage_useful_changes``): ``git add -A``
         then unstage runtime garbage (logs, caches, locks, SQLite, etc.).
      3. If nothing useful remains staged → return 1 (no-op, soft failure).
      4. Auto-generate a contextual commit message (``_build_commit_message``)
         unless an explicit one is supplied.

    Runtime ignored paths (runtime.log, daemon.log, *.lock, etc.) are *never*
    committed, regardless of how ``git add -A`` picks them up.
    """
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

    if include_code:
        print(f"staging (include-code): git add -A then unstage runtime garbage")
    else:
        print(f"staging: runs/{ticket_id}/ only")

    staged, dropped = _stage_useful_changes(ticket_id, include_code=include_code)

    if not staged:
        # Nothing useful staged. The auto loop treats rc=1 as "no-op",
        # rc=2 as "hard failure". A clean tree (after dropping runtime
        # garbage) is a no-op, not a failure.
        print(
            "nothing useful to commit (only runtime ignored files were dirty)",
            file=sys.stderr,
        )
        _log_runtime(
            ticket_id,
            "commit-checkpoint: nothing useful to commit"
            + (f" (dropped runtime: {dropped!r})" if dropped else ""),
        )
        return 1

    if message is None:
        message = _build_commit_message(ticket_id, workflow_step, current_state, staged)

    print(f"staged files ({len(staged)}):")
    for p in staged[:20]:
        print(f"  {p}")
    if len(staged) > 20:
        print(f"  … and {len(staged) - 20} more")

    commit_result = run_command(["git", "commit", "-m", message])
    rc = print_result(commit_result)
    if rc == 0:
        sha_result = run_command(["git", "rev-parse", "--short", "HEAD"])
        sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown"
        title = message.splitlines()[0]
        _log_runtime(ticket_id, f"commit-checkpoint: sha={sha} files={len(staged)} title={title!r}")
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

    # Blocking check: only *real* uncommitted code changes block the push.
    # Runtime garbage (runtime.log churning between commit and push, daemon
    # logs, caches, locks, SQLite live DB) is tolerated — these files would
    # otherwise reliably make the push fail every single cycle for purely
    # cosmetic reasons.
    wt_result = run_command(["git", "status", "--porcelain"])
    if wt_result.returncode == 0 and wt_result.stdout.strip():
        paths = parse_porcelain_paths(wt_result.stdout)
        ignorable, real = classify_intake_dirty_paths(paths)
        if real:
            msg = (
                "DIRTY_RUNTIME_CHECKPOINT — uncommitted real changes present "
                f"before push: {real!r}"
            )
            print(f"error: {msg}", file=sys.stderr)
            _log_runtime(ticket_id, f"push: refused — {msg}")
            return 2
        if ignorable:
            _log_runtime(
                ticket_id,
                f"push: tolerating runtime dirty files (not blocking): {ignorable!r}",
            )

    print(f"push branch: {push_target}")
    _log_runtime(ticket_id, f"push: pushing branch={push_target}")
    rc = run_git(["push", "-u", "origin", push_target])
    if rc == 0:
        _log_runtime(ticket_id, f"push: done branch={push_target}")
    else:
        _log_runtime(ticket_id, f"push: failed branch={push_target}")
    return rc


def archive_daemon(ticket_id: str) -> int:
    """Write daemon_archived=true to state.json to exclude ticket from daemon cycles."""
    path = _state_path(ticket_id)
    if not path.exists():
        print(f"error: state.json not found for {ticket_id}", file=sys.stderr)
        _log_runtime(ticket_id, "archive-daemon: refused — state.json not found")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"error: state.json corrupted for {ticket_id}", file=sys.stderr)
        _log_runtime(ticket_id, "archive-daemon: refused — state.json corrupted")
        return 2
    data["daemon_archived"] = True
    updated = {**data, "updated_at": _now_iso()}
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    tmp.rename(path)
    _log_runtime(ticket_id, "archive-daemon: daemon_archived=true")
    print(f"archived: {ticket_id} daemon_archived=true")
    return 0


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
    """Refuse a step only when *real* code changes are dirty.

    Runtime/generated artifacts produced by the workflow itself
    (runs/<ticket>/runtime.log, __pycache__/*.pyc, runs/.project-map*.json,
    runs/daemon.log, .runtime/*.sqlite, etc.) must not block the auto loop:
    they are classified via runtime_checkpoint.is_ignorable_runtime_dirty_path
    and tolerated. Any other dirty path still raises.
    """
    result = run_command(["git", "status", "--porcelain"])

    if result.returncode != 0:
        raise TicketRunnerError("failed to check git status")

    if not result.stdout.strip():
        return

    paths = parse_porcelain_paths(result.stdout)
    ignorable, real = classify_intake_dirty_paths(paths)

    if real:
        print("DEBUG dirty working tree:")
        print(result.stdout)

        raise TicketRunnerError(
            "working tree is not clean — commit or stash changes first"
        )

    if ignorable:
        print(f"clean gate: ignored runtime dirty files: {ignorable}")


def _checkpoint_planner_artifacts(ticket_id: str, push: bool) -> None:
    """Best-effort checkpoint of planner artifacts.

    The planner step writes ``runs/<ticket>/plan.md`` and
    ``runs/<ticket>/prompts/planner-attempt-N.md``. If we leave those uncommitted,
    the next daemon cycle's clean gate refuses to advance the ticket, which is
    the original bug this helper fixes. Errors are swallowed (logged only) so a
    transient git failure does not block the loop — the worst case is that
    the next cycle's clean gate will surface the issue with a real error.
    """
    try:
        checkpoint_transition(
            ticket_id,
            f"{ticket_id}: planner checkpoint",
            push=push,
        )
        _log_runtime(ticket_id, "planner checkpoint: committed")
        if push:
            _log_runtime(ticket_id, "planner checkpoint: pushed")
    except CheckpointError as exc:
        _log_runtime(ticket_id, f"planner checkpoint: skipped — {exc}")
    except DirtyTreeError as exc:
        _log_runtime(ticket_id, f"planner checkpoint: dirty tree after commit — {exc}")


def _determine_next_state(
    is_deterministic: bool,
    output: str,
    possible_next: list[str],
) -> str | None:
    if is_deterministic:
        return possible_next[0]
    found = [
        kw for kw in possible_next
        if re.search(
            rf"(?:^{re.escape(kw)}$"
            rf"|^\*\*{re.escape(kw)}\*\*$"
            rf"|^(?:Verdict|D[ée]cision|Decision)\s*:\s*{re.escape(kw)}\s*$)",
            output,
            re.MULTILINE,
        )
    ]
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
    project_root: Path | None = None,
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
    if project_root is not None:
        cmd += ["--project-root", str(project_root)]
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


def _write_fix_artifact(ticket_id: str, next_state: str, review_path: Path) -> None:
    """Create the next numbered fix artifact from the review content."""
    fixes_dir = Path("runs") / ticket_id / "fixes"
    fixes_dir.mkdir(parents=True, exist_ok=True)

    prefix = "plan-fix" if next_state == "PLAN_FIX_REQUIRED" else "implementation-fix"
    max_n = 0
    for p in fixes_dir.glob(f"{prefix}-*.md"):
        m = re.match(rf"^{re.escape(prefix)}-(\d+)\.md$", p.name)
        if m:
            max_n = max(max_n, int(m.group(1)))

    artifact_path = fixes_dir / f"{prefix}-{max_n + 1}.md"
    review_content = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    content = (
        f"# Fix artifact — {next_state}\n\n"
        f"- decision: {next_state}\n"
        f"- review source: {review_path}\n"
        f"- generated at: {_now_iso()}\n\n"
        f"---\n\n"
        f"{review_content.strip()}\n"
    )
    artifact_path.write_text(content, encoding="utf-8")
    print(f"auto-run: fix artifact written: {artifact_path}")
    _log_runtime(ticket_id, f"auto-run: fix artifact written: {artifact_path}")


_PLAN_FIX_ARTIFACT_ONLY_PREAMBLE = (
    "## Artifact-only instruction (mandatory)\n\n"
    "Your response will be written verbatim to `{artifact_path}`.\n"
    "Rewrite the artifact itself. Do not describe the modifications.\n"
    "Do not explain what changed. Do not produce a status report.\n"
    "Openings such as \"The plan has been rewritten…\", \"This plan now\n"
    "covers…\", \"Plan rewritten as…\", \"Key points covered…\", \"The\n"
    "document now…\" make the output invalid."
)


def _build_fix_context_file(
    ticket_id: str,
    artifacts: dict,
    current_state: str | None = None,
) -> Path:
    """Concatenate fix artifacts into a timestamped context file; return its path.

    When ``current_state == "PLAN_FIX_REQUIRED"`` the file starts with an
    explicit artifact-only preamble so the planner cannot mistake the fix
    context for a request to summarize its own changes.
    """
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_path = Path("runs") / ticket_id / "fixes" / f"context-{ts}.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    if current_state == "PLAN_FIX_REQUIRED":
        sections.append(
            _PLAN_FIX_ARTIFACT_ONLY_PREAMBLE.format(
                artifact_path=f"runs/{ticket_id}/plan.md"
            )
        )
    for key, label in [
        ("previous_output", "## Output précédent"),
        ("review", "## Review"),
        ("fix_instructions", "## Instructions de fix"),
    ]:
        content = artifacts[key].read_text(encoding="utf-8")
        sections.append(f"{label}\n\n{content.strip()}")

    context_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    return context_path


def _build_planner_meta_report_retry_context(ticket_id: str) -> Path:
    """Write a small artifact-only reinforcement file for the planner retry.

    Used after the validator classifies a planner output as a meta-report:
    the next attempt receives this file as ``--extra-context-file`` so the
    artifact-only rule is unmistakable.
    """
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_path = Path("runs") / ticket_id / "fixes" / f"meta-report-retry-{ts}.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "## Artifact-only retry instruction (mandatory)\n\n"
        f"Your previous response was classified as a meta-report about the\n"
        f"artifact rather than the artifact itself. Your next response will be\n"
        f"written verbatim to `runs/{ticket_id}/plan.md`.\n\n"
        "Rewrite the artifact itself. Do not describe the modifications.\n"
        "Do not explain what changed. Do not produce a status report.\n"
        "Do not open with \"The plan has been rewritten\", \"This plan now\",\n"
        "\"Plan rewritten as\", \"Key points covered\", \"The document now\",\n"
        "\"Plan written to\", \"`runs/<ticket>/plan.md` is written\",\n"
        "or any other meta-statement about your own work.\n"
        "Your reply MUST start with `## Objective` (or the French equivalent).\n"
    )
    context_path.write_text(content, encoding="utf-8")
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


def _resolve_project_id_from_state(state: dict) -> str | None:
    """Pick the project id used for runtime DB scoping.

    Prefers an explicit ``project_id`` in ``state.json``; falls back to the
    ``PROJECT_NAME`` env var — the same fallback used by ``run_daemon``.
    """
    project_id = state.get("project_id") if isinstance(state, dict) else None
    if project_id:
        return str(project_id)
    env_pid = os.environ.get("PROJECT_NAME")
    return env_pid or None


def _maybe_auto_approve_plan(ticket_id: str, state: dict) -> str | None:
    """Auto-approve the plan if the project has disabled the human plan gate.

    Returns the new state (``"PLAN_APPROVED"``) when auto-approval fires,
    ``None`` when the gate is kept (default behaviour) or when the lookup
    fails safely. All errors fall back to the human gate — the safe default.
    """
    try:
        # Deferred imports keep the CLI startup cost identical when the toggle
        # is untouched and avoid a circular import via the tools package.
        _tools_dir = Path(__file__).resolve().parent
        if str(_tools_dir) not in sys.path:
            sys.path.insert(0, str(_tools_dir))
        import execution_rules_engine  # noqa: WPS433
        import runtime_db  # noqa: WPS433
        import ticket_approval_service  # noqa: WPS433
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-approve: skipped — import failed: {exc}")
        return None

    project_id = _resolve_project_id_from_state(state)
    try:
        db_path = runtime_db.get_db_path(project_id=project_id)
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-approve: skipped — db path lookup failed: {exc}")
        return None
    if db_path is None:
        _log_runtime(ticket_id, "auto-approve: skipped — runtime DB not available")
        return None

    try:
        required = execution_rules_engine.is_human_plan_approval_required(
            db_path, project_id
        )
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-approve: skipped — rule lookup failed: {exc}")
        return None
    if required:
        return None

    _log_runtime(
        ticket_id,
        f"auto-approve: plan approval gate disabled for project={project_id!r}",
    )
    try:
        ticket_approval_service.auto_approve_plan(db_path, ticket_id)
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-approve: failed — {exc}")
        return None

    save_state(ticket_id, {**state, "state": "PLAN_APPROVED"})
    _append_workflow_journal(
        ticket_id, "PLAN_REVIEW_NEEDED", "auto-approve", "PLAN_APPROVED",
    )
    _log_runtime(
        ticket_id,
        "auto-run: transition PLAN_REVIEW_NEEDED → PLAN_APPROVED (auto, PROJECT_SETTING)",
    )
    return "PLAN_APPROVED"


# ── human approval ───────────────────────────────────────────────────────────

# Maps CLI command name → (required_current_state, target_state)
HUMAN_APPROVAL_TRANSITIONS: dict[str, tuple[str, str]] = {
    "approve-plan":               ("PLAN_REVIEW_NEEDED",           "PLAN_APPROVED"),
    "request-plan-fix":           ("PLAN_REVIEW_NEEDED",           "PLAN_FIX_REQUIRED"),
    "approve-implementation":     ("IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_APPROVED"),
    "request-implementation-fix": ("IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_FIX_REQUIRED"),
    "reject-conflict-resolution": ("CONFLICT_RESOLVED_REVIEW_NEEDED", "CONFLICT_RESOLUTION_NEEDED"),
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


def apply_approve_conflict_resolution(ticket_id: str) -> int:
    """Approve conflict resolution — restores pre_conflict_state from state.json."""
    try:
        state = load_state(ticket_id)
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    current_state = state["state"]
    if current_state != "CONFLICT_RESOLVED_REVIEW_NEEDED":
        print(
            f"error: --approve-conflict-resolution requires state "
            f"CONFLICT_RESOLVED_REVIEW_NEEDED, current state is {current_state!r}",
            file=sys.stderr,
        )
        _log_runtime(
            ticket_id,
            f"human-approval: refused approve-conflict-resolution — "
            f"expected CONFLICT_RESOLVED_REVIEW_NEEDED, got {current_state!r}",
        )
        return 2
    target_state = state.get("pre_conflict_state")
    if not target_state or target_state not in VALID_STATES:
        # Rebase can rewind tracked state.json and drop conflict metadata.
        # In the standard workflow, conflicts are detected after TEST_COMPLETE.
        inferred = "TEST_COMPLETE"
        if inferred in VALID_STATES:
            _log_runtime(
                ticket_id,
                f"human-approval: pre_conflict_state missing — inferring {inferred!r}",
            )
            target_state = inferred
        else:
            print(
                f"error: pre_conflict_state is missing or invalid in state.json: "
                f"{state.get('pre_conflict_state')!r}",
                file=sys.stderr,
            )
            _log_runtime(
                ticket_id,
                f"human-approval: refused approve-conflict-resolution — "
                f"pre_conflict_state={state.get('pre_conflict_state')!r} invalid",
            )
            return 2
    save_state(ticket_id, {**state, "state": target_state})
    _append_workflow_journal(ticket_id, current_state, "approve-conflict-resolution", target_state)
    _log_runtime(
        ticket_id,
        f"human-approval: approve-conflict-resolution — {current_state} → {target_state}",
    )
    print(f"approved: {current_state} → {target_state}")
    return 0


def _maybe_auto_finalize_conflict_resolution(ticket_id: str, state: dict) -> str | None:
    """Auto-approve conflict resolution and run PR lifecycle when configured.

    Returns the new workflow state (typically ``TEST_COMPLETE``) when
    auto-finalization runs, ``None`` when the human review gate is kept.
    """
    current_state = state.get("state")
    if current_state != "CONFLICT_RESOLVED_REVIEW_NEEDED":
        return None

    try:
        _tools_dir = Path(__file__).resolve().parent
        if str(_tools_dir) not in sys.path:
            sys.path.insert(0, str(_tools_dir))
        import execution_rules_engine  # noqa: WPS433
        import runtime_db  # noqa: WPS433
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-finalize-conflict: skipped — import failed: {exc}")
        return None

    project_id = _resolve_project_id_from_state(state)
    try:
        db_path = runtime_db.get_db_path(project_id=project_id)
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-finalize-conflict: skipped — db lookup failed: {exc}")
        return None
    if db_path is None:
        _log_runtime(ticket_id, "auto-finalize-conflict: skipped — runtime DB not available")
        return None

    try:
        required = execution_rules_engine.is_human_conflict_resolution_approval_required(
            db_path, project_id,
        )
    except Exception as exc:
        _log_runtime(ticket_id, f"auto-finalize-conflict: skipped — rule lookup failed: {exc}")
        return None
    if required:
        return None

    target_state = state.get("pre_conflict_state")
    if not target_state or target_state not in VALID_STATES:
        _log_runtime(
            ticket_id,
            f"auto-finalize-conflict: refused — invalid pre_conflict_state={target_state!r}",
        )
        return None

    _log_runtime(
        ticket_id,
        f"auto-finalize-conflict: gate disabled for project={project_id!r}",
    )
    save_state(ticket_id, {**state, "state": target_state})
    _append_workflow_journal(
        ticket_id,
        current_state,
        "auto-approve-conflict-resolution",
        target_state,
    )
    _log_runtime(
        ticket_id,
        f"conflict-resolver: transition {current_state} → {target_state} (auto, PROJECT_SETTING)",
    )

    if target_state == "TEST_COMPLETE":
        try:
            _finalize_test_complete_pr(ticket_id)
        except TicketRunnerError as exc:
            _log_runtime(ticket_id, f"auto-finalize-conflict: PR lifecycle failed: {exc}")

    return target_state


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

def _resolve_github_repo() -> str | None:
    """Return ``owner/repo`` for the current git checkout via ``gh``."""
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            owner_repo = data.get("nameWithOwner")
            if owner_repo:
                return str(owner_repo)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return None


def _finalize_test_complete_pr(ticket_id: str) -> None:
    """Create/merge PR and close issue — last step of the coding workflow."""
    state = load_state(ticket_id)
    if state.get("issue_closed") or state.get("pr_skipped_no_diff"):
        return

    import ticket_pr_lifecycle as pr  # noqa: WPS433

    run_dir = _state_path(ticket_id).parent
    repo = _resolve_github_repo()
    _log_runtime(ticket_id, "auto-run: TEST_COMPLETE — running PR lifecycle")
    pr.handle_test_complete(
        ticket_id,
        run_dir,
        repo,
        worktree_cwd=str(Path.cwd()),
    )


def auto_run(ticket_id: str, exec_cmd: str, auto_commit: bool = False, auto_push: bool = False, include_code: bool = False, project_root: Path | None = None) -> int:
    try:
        state = load_state(ticket_id)
    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    current_state = state["state"]
    _log_runtime(ticket_id, f"auto-run start: state={current_state}")

    # Gate 3: terminal state — finalize GitHub PR if the workflow stopped early
    if current_state == "TEST_COMPLETE":
        try:
            _finalize_test_complete_pr(ticket_id)
        except TicketRunnerError:
            pass
        print("workflow complete")
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
        # Distinct failure class so the daemon's retry policy can react
        # specifically to "dirty tree" loops (typically a missed checkpoint
        # by the previous run).
        if "working tree is not clean" in str(exc):
            _log_runtime(ticket_id, "runtime failure: dirty_tree")
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
        extra_context_file = _build_fix_context_file(ticket_id, artifacts, current_state)
        for key, path in artifacts.items():
            _log_runtime(ticket_id, f"auto-run: fix context: {key}={path}")
        _log_runtime(ticket_id, f"auto-run: fix context: context_file={extra_context_file}")

    if step == "review" and current_state in REVIEW_DECISION_KEYWORDS:
        extra_context_file = _build_review_decision_context_file(ticket_id, current_state)
        _log_runtime(ticket_id, f"auto-run: review decision context: context_file={extra_context_file}")

    rc, output_content, output_path = _call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state, project_root)
    _log_runtime(ticket_id, f"auto-run: step={step} done rc={rc}")

    if rc != 0:
        failure_class = classify_runtime_failure(rc, output_content, "")
        _log_runtime(ticket_id, f"auto-run: runtime failure: {failure_class} (rc={rc})")
        print(f"error: step '{step}' exited with code {rc} — state unchanged ({current_state})", file=sys.stderr)
        _log_runtime(ticket_id, f"auto-run: step={step} failed rc={rc}, state unchanged={current_state}")
        return 2

    if step == "planner":
        # Always checkpoint planner artifacts (plan.md + prompts/) before
        # validating so the working tree never stays dirty between cycles,
        # whether validation accepts or rejects. The rejected attempt stays
        # in git history for human inspection.
        _checkpoint_planner_artifacts(ticket_id, push=auto_push)

        reasons = validate_planner_output(output_content, artifact_type="plan")
        if reasons and META_REPORT_REASON in reasons:
            _log_runtime(ticket_id, "runtime warning: planner_meta_report_retry")
            retry_context = _build_planner_meta_report_retry_context(ticket_id)
            rc, output_content, output_path = _call_run_step(
                ticket_id, step, exec_cmd, retry_context, current_state, project_root,
            )
            _log_runtime(ticket_id, f"auto-run: step={step} retry done rc={rc}")
            if rc != 0:
                failure_class = classify_runtime_failure(rc, output_content, "")
                _log_runtime(ticket_id, f"auto-run: runtime failure: {failure_class} (rc={rc})")
                _log_runtime(ticket_id, "runtime failure: planner_invalid")
                print(
                    f"error: step '{step}' retry exited with code {rc} — state unchanged ({current_state})",
                    file=sys.stderr,
                )
                return 2
            _checkpoint_planner_artifacts(ticket_id, push=auto_push)
            reasons = validate_planner_output(output_content, artifact_type="plan")

        if reasons:
            for reason in reasons:
                _log_runtime(ticket_id, f"planner validation failed: {reason}")
                print(f"error: planner output invalid: {reason}", file=sys.stderr)
            _log_runtime(ticket_id, "planner validation: rejected — state unchanged")
            # Distinct failure class for retry policy (see _RETRY_POLICIES in run_daemon)
            _log_runtime(ticket_id, "runtime failure: planner_invalid")
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
        print(f"auto-run: review keyword detected: {next_state}")
        _log_runtime(ticket_id, f"auto-run: review keyword detected: {next_state}")

    save_state(ticket_id, {**state, "state": next_state})
    _append_workflow_journal(ticket_id, current_state, step, next_state)
    _log_runtime(ticket_id, f"auto-run: transition {current_state} → {next_state}")
    print(f"[auto] {current_state} → {next_state}")

    if step == "planner" and next_state == "PLAN_REVIEW_NEEDED":
        auto_next = _maybe_auto_approve_plan(
            ticket_id, {**state, "state": next_state}
        )
        if auto_next is not None:
            next_state = auto_next
            print(f"[auto] PLAN_REVIEW_NEEDED → {next_state}")

    if next_state.endswith("_FIX_REQUIRED"):
        _write_fix_artifact(ticket_id, next_state, output_path)

    if auto_commit:
        # Sematically, "auto-commit" means "commit *every* useful change the
        # workflow just produced". Restricting the staging surface here is
        # what caused T122: the coder modified apps/dashboard/, services/…
        # but `commit_ticket(include_code=False)` only staged
        # `runs/<ticket>/`, leaving real code dirty and breaking the next
        # `git pull --rebase`. We therefore always stage the full set when
        # auto-commit is enabled. The narrow `runs/<ticket>/`-only mode is
        # still reachable via manual `--commit` (without `--include-code`).
        effective_include_code = True if auto_commit else include_code
        _log_runtime(
            ticket_id,
            f"auto-run: auto-commit triggered (step={step}, include_code={effective_include_code})",
        )
        commit_rc = commit_ticket(
            ticket_id,
            None,
            include_code=effective_include_code,
            workflow_step=step,
        )
        if commit_rc == 0 and auto_push:
            _log_runtime(ticket_id, "auto-run: auto-push triggered")
            push_rc = push_branch(ticket_id, None)
            if push_rc != 0:
                print(f"warning: auto-push failed (rc={push_rc}) — state saved", file=sys.stderr)
                _log_runtime(ticket_id, f"auto-run: auto-push failed rc={push_rc}")
        elif commit_rc not in (0, 1):
            print(f"warning: auto-commit failed (rc={commit_rc}) — state saved, push skipped", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: auto-commit failed rc={commit_rc}")

    if next_state == "TEST_COMPLETE":
        try:
            _finalize_test_complete_pr(ticket_id)
        except TicketRunnerError as exc:
            print(f"warning: PR lifecycle failed: {exc}", file=sys.stderr)
            _log_runtime(ticket_id, f"auto-run: PR lifecycle failed: {exc}")

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
    parser.add_argument("--checkpoint", action="store_true", help="Alias for --commit (checkpoint runs/ artifacts)")
    parser.add_argument("--commit-message", help="Custom commit message")
    parser.add_argument("--include-code", action="store_true", help="With --commit, also stage COMMIT_SCOPE paths (tools/, tests/, prompts/, tickets/, docs/, ai/)")
    parser.add_argument("--archive-daemon", action="store_true", dest="archive_daemon", help="Mark daemon_archived=true in state.json to skip daemon processing")
    parser.add_argument("--push", action="store_true", help="Push the ticket branch (verified against state.json)")
    parser.add_argument("--auto", action="store_true", help="Execute next workflow step (reads state.json)")
    parser.add_argument("--auto-init", action="store_true", help="Initialize state.json for --auto mode")
    parser.add_argument("--ticket-source", help="Path to local ticket file to snapshot into runs/TXXX/ticket.md (use with --auto-init)")
    parser.add_argument("--auto-commit", action="store_true", help="After each successful --auto step, commit runs/ artifacts")
    parser.add_argument("--auto-push", action="store_true", help="After each successful --auto-commit, push the ticket branch")
    parser.add_argument("--auto-include-code", action="store_true", help="With --auto-commit, also stage COMMIT_SCOPE paths (tools/, tests/, prompts/, tickets/, docs/, ai/)")
    parser.add_argument("--repo-root", help="Path to main repo root (used when running from a worktree)")
    parser.add_argument("--project-root", help="Absolute path to a managed project root; context files (ai/, docs/) are resolved from there first")
    parser.add_argument("--set-state", help="Manually set workflow state (human review path)")
    parser.add_argument("--approve-plan", action="store_true", help="Approve plan (PLAN_REVIEW_NEEDED → PLAN_APPROVED)")
    parser.add_argument("--request-plan-fix", action="store_true", help="Request plan fix (PLAN_REVIEW_NEEDED → PLAN_FIX_REQUIRED)")
    parser.add_argument("--approve-implementation", action="store_true", help="Approve implementation (IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_APPROVED)")
    parser.add_argument("--request-implementation-fix", action="store_true", help="Request implementation fix (IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_FIX_REQUIRED)")
    parser.add_argument("--approve-conflict-resolution", action="store_true", help="Approve conflict resolution (CONFLICT_RESOLVED_REVIEW_NEEDED → pre_conflict_state)")
    parser.add_argument("--reject-conflict-resolution", action="store_true", help="Reject conflict resolution (CONFLICT_RESOLVED_REVIEW_NEEDED → CONFLICT_RESOLUTION_NEEDED)")
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
            ("reject-conflict-resolution", "reject_conflict_resolution"),
        ):
            if getattr(args, attr):
                return apply_human_approval(ticket_id, cmd)

        if args.approve_conflict_resolution:
            return apply_approve_conflict_resolution(ticket_id)

        if args.archive_daemon:
            return archive_daemon(ticket_id)

        if args.auto_init:
            return init_auto(ticket_id, args.branch_slug, getattr(args, "ticket_source", None))

        if args.branch or args.ensure_branch:
            return checkout_branch(ticket_id, args.branch_slug)

        if args.commit or args.checkpoint:
            return commit_ticket(ticket_id, args.commit_message, include_code=args.include_code)

        if args.push:
            return push_branch(ticket_id, args.branch_slug)

        if args.auto:
            if not args.exec_cmd:
                print("error: --exec-cmd is required with --auto", file=sys.stderr)
                return 2
            project_root = Path(args.project_root).resolve() if getattr(args, "project_root", None) else None
            return auto_run(ticket_id, args.exec_cmd, auto_commit=args.auto_commit, auto_push=args.auto_push, include_code=args.auto_include_code, project_root=project_root)

        if args.once:
            if not args.exec_cmd:
                print("error: --exec-cmd is required with --once", file=sys.stderr)
                return 2
            project_root = Path(args.project_root).resolve() if getattr(args, "project_root", None) else None
            return execute_once(ticket_id, args.once, args.exec_cmd, project_root=project_root)

        return show_next(ticket_id)

    except TicketRunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
