"""Tests for the planner auto-checkpoint and failure-class logging (T118 follow-up).

These cover the four runtime/planner bug fixes:

1. Planner output dirty tree no longer blocks the next cycle because
   ``_checkpoint_planner_artifacts`` always commits ``runs/<ticket>/`` after
   the planner step, even when the produced plan is rejected by
   ``validate_planner_output``.
2. ``runtime failure: planner_invalid`` is logged when validation rejects so
   the daemon retry policy can react.
3. ``runtime failure: dirty_tree`` is logged when the clean gate refuses.
4. Meta-report retry-once path (T202): when the planner returns a
   description of its own work instead of the artifact, the runner retries
   the step once with an artifact-only reinforcement before failing.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

import run_ticket
from run_ticket import (
    _checkpoint_planner_artifacts,
    CheckpointError,
    DirtyTreeError,
)


# ── _checkpoint_planner_artifacts (Fix 1) ────────────────────────────────────

def test_checkpoint_planner_artifacts_calls_checkpoint_transition(tmp_path):
    orig = Path.cwd()
    log_path = tmp_path / "runs" / "T001" / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import os
    os.chdir(tmp_path)
    try:
        with patch("run_ticket.checkpoint_transition") as mock_ck:
            _checkpoint_planner_artifacts("T001", push=True)
        mock_ck.assert_called_once()
        args, kwargs = mock_ck.call_args
        assert args[0] == "T001"
        assert "planner checkpoint" in args[1]
        assert kwargs.get("push") is True
    finally:
        os.chdir(orig)


def test_checkpoint_planner_artifacts_swallows_checkpoint_error(tmp_path):
    """A failed checkpoint must not raise — only log — so the auto loop keeps going."""
    import os
    orig = os.getcwd()
    (tmp_path / "runs" / "T001").mkdir(parents=True)
    os.chdir(tmp_path)
    try:
        with patch(
            "run_ticket.checkpoint_transition",
            side_effect=CheckpointError("nothing staged"),
        ):
            _checkpoint_planner_artifacts("T001", push=False)  # must not raise
        log = (tmp_path / "runs" / "T001" / "runtime.log").read_text()
        assert "planner checkpoint: skipped" in log
    finally:
        os.chdir(orig)


def test_checkpoint_planner_artifacts_swallows_dirty_tree_error(tmp_path):
    import os
    orig = os.getcwd()
    (tmp_path / "runs" / "T001").mkdir(parents=True)
    os.chdir(tmp_path)
    try:
        with patch(
            "run_ticket.checkpoint_transition",
            side_effect=DirtyTreeError("DIRTY_RUNTIME_CHECKPOINT — foo"),
        ):
            _checkpoint_planner_artifacts("T001", push=True)  # must not raise
        log = (tmp_path / "runs" / "T001" / "runtime.log").read_text()
        assert "dirty tree after commit" in log
    finally:
        os.chdir(orig)


# ── failure-class logging (Fix 4) ────────────────────────────────────────────

def test_dirty_tree_failure_class_message_is_recognised():
    """The exact string ``runtime failure: dirty_tree`` must appear in the log
    so the daemon's regex (``runtime failure: (\\w+)``) classifies it as
    ``dirty_tree``.
    """
    import re
    log_line = "[2026-01-01T00:00:00Z] runtime failure: dirty_tree"
    match = re.search(r"runtime failure: (\w+)", log_line)
    assert match is not None
    assert match.group(1) == "dirty_tree"


def test_planner_invalid_failure_class_message_is_recognised():
    import re
    log_line = "[2026-01-01T00:00:00Z] runtime failure: planner_invalid"
    match = re.search(r"runtime failure: (\w+)", log_line)
    assert match is not None
    assert match.group(1) == "planner_invalid"


# ── meta-report retry-once path (T202) ───────────────────────────────────────

_META_REPORT_OUTPUT = (
    "The plan has been rewritten as a real implementation document. "
    "Key points covered include the objective, the scope, the exclusions "
    "and the acceptance criteria. The plan now contains a clear set of "
    "steps for the coder to follow."
)

_VALID_PLAN_OUTPUT = (
    "## Objective\n"
    "Rename foo to bar in the utils module — behaviour preserving.\n\n"
    "## Included\n"
    "- utils.py: rename helper\n\n"
    "## Excluded\n"
    "- callers in other modules\n\n"
    "## Acceptance criteria\n"
    "- tests pass; module no longer exports the old name\n"
)


def _setup_auto_run_state(tmp_path: Path, ticket: str = "T999") -> Path:
    run_dir = tmp_path / "runs" / ticket
    run_dir.mkdir(parents=True)
    state_path = run_dir / "state.json"
    state_path.write_text(
        json.dumps({
            "ticket_id": ticket,
            "state": "PLAN_FIX_REQUIRED",
            "branch": f"ticket/{ticket}-test",
            "updated_at": "2026-06-21T00:00:00Z",
        }),
        encoding="utf-8",
    )
    return run_dir


def test_planner_meta_report_triggers_retry_once_and_succeeds(tmp_path):
    """First planner call returns a meta-report; the runner must retry the
    step exactly once with an artifact-only reinforcement, the second call
    returns a valid plan, and auto_run ends with rc=0.
    """
    ticket = "T999"
    run_dir = _setup_auto_run_state(tmp_path, ticket)
    orig = os.getcwd()
    os.chdir(tmp_path)

    calls: list[Path | None] = []

    def fake_call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state, project_root):
        calls.append(extra_context_file)
        if len(calls) == 1:
            return 0, _META_REPORT_OUTPUT, Path(f"runs/{ticket_id}/plan.md")
        return 0, _VALID_PLAN_OUTPUT, Path(f"runs/{ticket_id}/plan.md")

    fake_artifacts = {
        "previous_output": tmp_path / "prev.md",
        "review": tmp_path / "rev.md",
        "fix_instructions": tmp_path / "fix.md",
    }
    for p in fake_artifacts.values():
        p.write_text("placeholder", encoding="utf-8")

    try:
        with patch("run_ticket._get_current_branch", return_value=f"ticket/{ticket}-test"), \
             patch("run_ticket._check_working_tree_clean"), \
             patch("run_ticket._collect_fix_artifacts", return_value=fake_artifacts), \
             patch("run_ticket._call_run_step", side_effect=fake_call_run_step), \
             patch("run_ticket._checkpoint_planner_artifacts"):
            rc = run_ticket.auto_run(ticket, "/bin/true")
    finally:
        os.chdir(orig)

    assert rc == 0
    assert len(calls) == 2, f"planner must be retried exactly once, got {len(calls)} calls"
    # The retry must use the dedicated artifact-only reinforcement context,
    # not the original fix context.
    assert calls[1] is not None
    assert "meta-report-retry-" in str(calls[1])

    log_text = (run_dir / "runtime.log").read_text(encoding="utf-8")
    assert "runtime warning: planner_meta_report_retry" in log_text
    assert "planner validation success" in log_text
    # Retry warning must precede the eventual success line.
    assert log_text.index("runtime warning: planner_meta_report_retry") < log_text.index(
        "planner validation success"
    )
    # The transition must have been recorded.
    assert "PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED" in log_text


def test_planner_meta_report_retry_failing_again_logs_planner_invalid(tmp_path):
    """If the retry also returns a meta-report, the runner must log
    ``runtime failure: planner_invalid`` and exit with rc=2 — no second
    retry.
    """
    ticket = "T998"
    run_dir = _setup_auto_run_state(tmp_path, ticket)
    orig = os.getcwd()
    os.chdir(tmp_path)

    calls: list[Path | None] = []

    def fake_call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state, project_root):
        calls.append(extra_context_file)
        return 0, _META_REPORT_OUTPUT, Path(f"runs/{ticket_id}/plan.md")

    fake_artifacts = {
        "previous_output": tmp_path / "prev.md",
        "review": tmp_path / "rev.md",
        "fix_instructions": tmp_path / "fix.md",
    }
    for p in fake_artifacts.values():
        p.write_text("placeholder", encoding="utf-8")

    try:
        with patch("run_ticket._get_current_branch", return_value=f"ticket/{ticket}-test"), \
             patch("run_ticket._check_working_tree_clean"), \
             patch("run_ticket._collect_fix_artifacts", return_value=fake_artifacts), \
             patch("run_ticket._call_run_step", side_effect=fake_call_run_step), \
             patch("run_ticket._checkpoint_planner_artifacts"):
            rc = run_ticket.auto_run(ticket, "/bin/true")
    finally:
        os.chdir(orig)

    assert rc == 2
    assert len(calls) == 2, "planner must be retried exactly once even when retry also fails"
    log_text = (run_dir / "runtime.log").read_text(encoding="utf-8")
    assert "runtime warning: planner_meta_report_retry" in log_text
    assert "runtime failure: planner_invalid" in log_text


# ── plan.md must change after PLAN_FIX_REQUIRED ──────────────────────────────


def test_plan_fix_rejects_unchanged_plan_md(tmp_path):
    """A chatty planner that leaves plan.md untouched must be rejected."""
    ticket = "T997"
    run_dir = _setup_auto_run_state(tmp_path, ticket)
    plan_path = run_dir / "plan.md"
    plan_path.write_text(_VALID_PLAN_OUTPUT, encoding="utf-8")

    orig = os.getcwd()
    os.chdir(tmp_path)

    def fake_call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state, project_root):
        # Simulate prefer-on-disk: return valid content without rewriting the file.
        return 0, _VALID_PLAN_OUTPUT, Path(f"runs/{ticket_id}/plan.md")

    fake_artifacts = {
        "previous_output": tmp_path / "prev.md",
        "review": tmp_path / "rev.md",
        "fix_instructions": tmp_path / "fix.md",
    }
    for p in fake_artifacts.values():
        p.write_text("placeholder", encoding="utf-8")

    try:
        with patch("run_ticket._get_current_branch", return_value=f"ticket/{ticket}-test"), \
             patch("run_ticket._check_working_tree_clean"), \
             patch("run_ticket._collect_fix_artifacts", return_value=fake_artifacts), \
             patch("run_ticket._call_run_step", side_effect=fake_call_run_step), \
             patch("run_ticket._checkpoint_planner_artifacts"):
            rc = run_ticket.auto_run(ticket, "/bin/true")
    finally:
        os.chdir(orig)

    assert rc == 2
    log_text = (run_dir / "runtime.log").read_text(encoding="utf-8")
    assert run_ticket.PLAN_UNCHANGED_REASON in log_text
    assert "runtime failure: planner_invalid" in log_text
    assert "PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED" not in log_text
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "PLAN_FIX_REQUIRED"


def test_plan_fix_accepts_changed_plan_md(tmp_path):
    """When plan.md is rewritten, PLAN_FIX_REQUIRED may advance."""
    ticket = "T996"
    run_dir = _setup_auto_run_state(tmp_path, ticket)
    plan_path = run_dir / "plan.md"
    plan_path.write_text(_VALID_PLAN_OUTPUT + "\n# old\n", encoding="utf-8")

    revised = (
        "## Objective\n"
        "Rename foo to bar and update callers — behaviour preserving.\n\n"
        "## Included\n"
        "- utils.py: rename helper\n"
        "- callers: update imports\n\n"
        "## Excluded\n"
        "- unrelated modules\n\n"
        "## Acceptance criteria\n"
        "- tests pass; old name gone from public API\n"
    )

    orig = os.getcwd()
    os.chdir(tmp_path)

    def fake_call_run_step(ticket_id, step, exec_cmd, extra_context_file, current_state, project_root):
        Path(f"runs/{ticket_id}/plan.md").write_text(revised, encoding="utf-8")
        return 0, revised, Path(f"runs/{ticket_id}/plan.md")

    fake_artifacts = {
        "previous_output": tmp_path / "prev.md",
        "review": tmp_path / "rev.md",
        "fix_instructions": tmp_path / "fix.md",
    }
    for p in fake_artifacts.values():
        p.write_text("placeholder", encoding="utf-8")

    try:
        with patch("run_ticket._get_current_branch", return_value=f"ticket/{ticket}-test"), \
             patch("run_ticket._check_working_tree_clean"), \
             patch("run_ticket._collect_fix_artifacts", return_value=fake_artifacts), \
             patch("run_ticket._call_run_step", side_effect=fake_call_run_step), \
             patch("run_ticket._checkpoint_planner_artifacts"):
            rc = run_ticket.auto_run(ticket, "/bin/true")
    finally:
        os.chdir(orig)

    assert rc == 0
    log_text = (run_dir / "runtime.log").read_text(encoding="utf-8")
    assert "planner validation success" in log_text
    assert run_ticket.PLAN_UNCHANGED_REASON not in log_text
    assert "PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED" in log_text
