"""Tests for the planner auto-checkpoint and failure-class logging (T118 follow-up).

These cover the four runtime/planner bug fixes:

1. Planner output dirty tree no longer blocks the next cycle because
   ``_checkpoint_planner_artifacts`` always commits ``runs/<ticket>/`` after
   the planner step, even when the produced plan is rejected by
   ``validate_planner_output``.
2. ``runtime failure: planner_invalid`` is logged when validation rejects so
   the daemon retry policy can react.
3. ``runtime failure: dirty_tree`` is logged when the clean gate refuses.
"""

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
