"""Regression tests for the runtime hardening of auto-commit and auto-push.

What these tests guarantee:

1. ``is_runtime_ignored_path`` is the single source of truth for "runtime
   garbage" and covers all paths the user listed: ``runtime.log``,
   ``daemon.log``, ``daemon.lock``, ``__pycache__/``, ``*.pyc``,
   ``.pytest_cache/``, ``.runtime/*.sqlite*``.
2. ``commit_ticket(include_code=True)`` runs ``git add -A`` then unstages
   runtime paths picked up by ``git add -A``. Useful code/test/dashboard
   changes survive the unstage pass.
3. ``commit_ticket`` returns 1 (no-op, not failure) when the only dirty
   files are runtime ignored — the auto loop must not treat this as a
   hard failure.
4. ``push_branch`` is not blocked by a dirty ``runtime.log``.
5. ``_build_commit_message`` produces a message that contains the ticket id
   and a useful summary derived from the staged files.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import (
    commit_ticket,
    push_branch,
    is_runtime_ignored_path,
    _build_commit_message,
    _infer_commit_type,
    _summarize_scope,
)


# ── 1. centralised runtime-ignored helper ─────────────────────────────────────

def test_is_runtime_ignored_path_covers_user_listed_paths():
    """Every path the user explicitly listed in the runtime-hardening request
    must be classified as runtime-ignored."""
    must_be_ignored = [
        "runs/T120/runtime.log",
        "runs/T001/runtime.log",
        "runs/daemon.log",
        "runs/daemon.lock",
        "runs/T120/daemon.lock",
        "tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc",
        "services/control_api/__pycache__/board_service.cpython-314.pyc",
        "tools/__pycache__",
        ".pytest_cache/v/cache/lastfailed",
        ".pytest_cache/CACHEDIR.TAG",
        ".runtime/ai-dev-factory.sqlite",
        ".runtime/ai-dev-factory.sqlite-wal",
        ".runtime/ai-dev-factory.sqlite-shm",
        "runs/.project-map.json",
        "runs/.project-map-activity.json",
        "runs/workers.json",
        "runs/.issue-intake.json",
        "runs/daemon.pid",
        "backend/timizer_backend.egg-info/PKG-INFO",
        "backend/timizer_backend.egg-info/SOURCES.txt",
        "backend/pkg.dist-info/METADATA",
    ]
    for path in must_be_ignored:
        assert is_runtime_ignored_path(path), f"{path!r} must be runtime-ignored"


def test_is_runtime_ignored_path_does_not_flag_real_code():
    """Real source/test/doc files must *not* be classified as runtime-ignored."""
    real_paths = [
        "tools/agent_runner/run_ticket.py",
        "tools/agent_runner/runtime_checkpoint.py",
        "tests/test_run_ticket.py",
        "services/control_api/services/board_service.py",
        "apps/dashboard/src/App.tsx",
        "prompts/generic/planner.md",
        "docs/daemon-lifecycle.md",
        "runs/T120/plan.md",
        "runs/T120/reviews/plan-review.md",
        "runs/T120/tests/test-report.md",
        "README.md",
        ".gitignore",
    ]
    for path in real_paths:
        assert not is_runtime_ignored_path(path), f"{path!r} must NOT be runtime-ignored"


# ── 2. commit_ticket(include_code=True) uses git add -A + unstage runtime ────

def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _write_state(run_dir: Path, branch: str = "ticket/T999-work") -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "ticket_id": "T999",
        "state": "IMPLEMENTATION_REVIEW_NEEDED",
        "branch": branch,
        "updated_at": "2026-01-01T00:00:00Z",
    }))


def test_auto_commit_include_code_runs_git_add_dash_A():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999")
            calls = []

            def fake(args):
                calls.append(list(args))
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "diff", "--cached", "--name-only"]:
                    return _cp("tools/agent_runner/run_ticket.py\n")
                if args[:2] == ["git", "add"]:
                    return _cp()
                if args[:2] == ["git", "commit"]:
                    return _cp("1 file changed")
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None, include_code=True, workflow_step="coder")

            assert rc == 0
            add_calls = [c for c in calls if c[:2] == ["git", "add"]]
            assert ["git", "add", "-A"] in add_calls, (
                "include_code=True must run `git add -A`"
            )
        finally:
            os.chdir(orig)


def test_auto_commit_unstages_runtime_garbage_after_git_add_A():
    """After `git add -A`, runtime.log / pyc / lock paths must be unstaged."""
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999")
            reset_paths: list[str] = []

            staged_before_reset = [
                "tools/agent_runner/run_ticket.py",
                "runs/T999/runtime.log",
                "runs/T999/plan.md",
                "tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc",
                ".pytest_cache/v/cache/lastfailed",
                "runs/daemon.log",
            ]
            useful_after_reset = [
                "tools/agent_runner/run_ticket.py",
                "runs/T999/plan.md",
            ]
            staged_state = {"value": "\n".join(staged_before_reset) + "\n"}

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "diff", "--cached", "--name-only"]:
                    return _cp(staged_state["value"])
                if args[:2] == ["git", "add"]:
                    return _cp()
                if args[:3] == ["git", "reset", "HEAD"]:
                    # args == ["git", "reset", "HEAD", "--", path]
                    reset_paths.append(args[-1])
                    # After resets, the staged state shrinks to useful files only
                    staged_state["value"] = "\n".join(useful_after_reset) + "\n"
                    return _cp()
                if args[:2] == ["git", "commit"]:
                    return _cp("ok")
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None, include_code=True, workflow_step="coder")

            assert rc == 0
            for runtime_path in [
                "runs/T999/runtime.log",
                "tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc",
                ".pytest_cache/v/cache/lastfailed",
                "runs/daemon.log",
            ]:
                assert runtime_path in reset_paths, (
                    f"runtime path {runtime_path!r} must be unstaged"
                )
            # Useful code change must NOT be unstaged
            assert "tools/agent_runner/run_ticket.py" not in reset_paths
            assert "runs/T999/plan.md" not in reset_paths
        finally:
            os.chdir(orig)


def test_auto_commit_returns_1_when_only_runtime_is_dirty():
    """When the only staged-then-unstaged files are runtime garbage, the
    commit is a no-op (rc=1), not a hard failure (rc=2)."""
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999")

            # First call: returns runtime garbage only. After unstage, empty.
            staged_state = {"value": "runs/T999/runtime.log\nruns/daemon.log\n"}

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "diff", "--cached", "--name-only"]:
                    return _cp(staged_state["value"])
                if args[:2] == ["git", "add"]:
                    return _cp()
                if args[:3] == ["git", "reset", "HEAD"]:
                    staged_state["value"] = ""  # all unstaged
                    return _cp()
                if args[:2] == ["git", "commit"]:
                    raise AssertionError("commit must not run when nothing useful is staged")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None, include_code=True)

            assert rc == 1, "runtime-only dirty tree must be a no-op (rc=1)"
        finally:
            os.chdir(orig)


# ── 3. push tolerates runtime dirty ──────────────────────────────────────────

def test_push_not_blocked_by_runtime_log_dirty():
    """A dirty runtime.log must not block the push — the workflow itself
    mutates runtime.log between commit and push."""
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999")
            push_calls = []

            def fake(args, **kwargs):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "status", "--porcelain"]:
                    return _cp(
                        " M runs/T999/runtime.log\n"
                        " M runs/daemon.log\n"
                        " M tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc\n"
                    )
                if "push" in args:
                    push_calls.append(list(args))
                    return _cp("pushed")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = push_branch("T999", None)

            assert rc == 0, "push must succeed when only runtime files are dirty"
            assert len(push_calls) == 1
        finally:
            os.chdir(orig)


def test_push_still_blocked_by_real_code_dirty():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999")

            def fake(args, **kwargs):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "status", "--porcelain"]:
                    return _cp(
                        " M runs/T999/runtime.log\n"
                        " M tools/agent_runner/run_ticket.py\n"
                    )
                if "push" in args:
                    raise AssertionError("push must not run when real code is dirty")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = push_branch("T999", None)

            assert rc == 2
        finally:
            os.chdir(orig)


# ── 4. contextual commit message ─────────────────────────────────────────────

def test_commit_message_contains_ticket_id_and_step():
    msg = _build_commit_message(
        "T120",
        workflow_step="coder",
        workflow_state="IMPLEMENTATION_REVIEW_NEEDED",
        staged=[
            "services/control_api/services/board_service.py",
            "apps/dashboard/src/App.tsx",
            "tests/test_board_service.py",
            "runs/T120/plan.md",
        ],
    )
    title = msg.splitlines()[0]
    assert "T120" in title
    assert "coder" in title.lower()
    assert "refs T120" in msg
    body = "\n".join(msg.splitlines()[1:])
    assert "services/control_api/services/board_service.py" in body
    assert "apps/dashboard/src/App.tsx" in body


def test_commit_message_for_coder_step_is_feat():
    msg = _build_commit_message(
        "T120",
        workflow_step="coder",
        workflow_state="IMPLEMENTATION_REVIEW_NEEDED",
        staged=["services/control_api/services/board_service.py"],
    )
    assert msg.startswith("feat(T120/")


def test_commit_message_for_planner_step_is_docs():
    msg = _build_commit_message(
        "T120",
        workflow_step="planner",
        workflow_state="PLAN_REVIEW_NEEDED",
        staged=["runs/T120/plan.md", "runs/T120/prompts/planner-attempt-1.md"],
    )
    assert msg.startswith("docs(T120/")


def test_commit_message_for_tester_step_is_test():
    msg = _build_commit_message(
        "T120",
        workflow_step="tester",
        workflow_state="TEST_COMPLETE",
        staged=["runs/T120/tests/test-report.md"],
    )
    assert msg.startswith("test(T120/")


def test_commit_message_fallback_for_empty_staged():
    msg = _build_commit_message("T120", None, "PLAN_APPROVED", staged=[])
    assert "T120" in msg
    assert "checkpoint" in msg.lower()


def test_summarize_scope_collapses_dashboard_and_api():
    label = _summarize_scope(
        [
            "apps/dashboard/src/App.tsx",
            "apps/dashboard/src/components/Foo.tsx",
            "services/control_api/services/board_service.py",
        ],
        "T120",
    )
    assert "dashboard" in label
    assert "control-api" in label


def test_infer_commit_type_for_runs_only_is_chore():
    assert _infer_commit_type("review", ["runs/T120/reviews/review.md"]) == "chore"
    assert _infer_commit_type(None, ["runs/T120/plan.md"]) == "chore"
