"""Regression tests for the coder auto-commit lifecycle (T122 hardening).

Failure mode reproduced from production:
- coder modified real implementation files (apps/dashboard/, services/…);
- run_ticket completed the step, transitioned to IMPLEMENTATION_REVIEW_NEEDED;
- ``commit_ticket(include_code=False)`` only staged ``runs/<ticket>/`` and
  left every code file dirty;
- the next daemon cycle's ``git pull --rebase`` aborted with
  ``cannot pull with rebase: You have unstaged changes``.

This module verifies the four invariants that resolve the failure:

1. ``auto_run`` *always* uses ``include_code=True`` for auto-commit, even when
   the CLI omitted ``--auto-include-code``.
2. ``commit_ticket(include_code=True)`` stages real code files
   (apps/dashboard, services/control_api, …) and excludes runtime garbage
   (runtime.log, .pyc, .pytest_cache, .runtime/sqlite, locks).
3. The pre-sync hygiene of ``_sync_ticket_branch`` auto-commits any
   remaining useful dirty paths before rebase when ``auto_commit=True``,
   and refuses the rebase otherwise.
4. The generated commit message includes the ticket id and a useful
   scope summary (dashboard, control-api, …).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


TOOLS_DIR = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(TOOLS_DIR))


def _load_run_daemon():
    spec = importlib.util.spec_from_file_location(
        "_t122_run_daemon", TOOLS_DIR / "run_daemon.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_run_ticket():
    spec = importlib.util.spec_from_file_location(
        "_t122_run_ticket", TOOLS_DIR / "run_ticket.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _write_state(run_dir: Path, branch: str = "ticket/T122-work", state: str = "PLAN_APPROVED"):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "ticket_id": "T122",
        "state": state,
        "branch": branch,
        "updated_at": "2026-01-01T00:00:00Z",
    }))


# ── 1. auto_run forces include_code=True when auto_commit ─────────────────────

def test_auto_run_forces_include_code_when_auto_commit():
    """Even with ``include_code=False`` from the CLI, an auto-commit must
    stage code (else T122 reproduces). The ``commit_ticket`` call must be
    invoked with ``include_code=True``."""
    rt = _load_run_ticket()

    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T122"
            run_dir.mkdir(parents=True)
            (run_dir / "state.json").write_text(json.dumps({
                "ticket_id": "T122",
                "state": "PLAN_APPROVED",
                "branch": "ticket/T122-work",
                "updated_at": "2026-01-01T00:00:00Z",
            }))

            commit_calls: list[dict] = []

            def fake_commit_ticket(ticket_id, message, **kwargs):
                commit_calls.append({"ticket_id": ticket_id, **kwargs})
                return 0

            def fake_run_command(args, cwd=None):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T122-work\n")
                if args == ["git", "status", "--porcelain"]:
                    return _cp("")  # clean
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            # _call_run_step succeeds with a minimal coder output (planner output
            # is not used here because coder is deterministic — no review keyword).
            def fake_call_run_step(ticket_id, step, exec_cmd, extra_context_file=None, current_state=None):
                return 0, "ok", Path("runs") / ticket_id / "implementation-output.md"

            with patch.object(rt, "commit_ticket", side_effect=fake_commit_ticket), \
                 patch.object(rt, "run_command", side_effect=fake_run_command), \
                 patch.object(rt, "_call_run_step", side_effect=fake_call_run_step), \
                 patch.object(rt, "_checkpoint_planner_artifacts"), \
                 patch.object(rt, "_log_runtime"), \
                 patch.object(rt, "_append_workflow_journal"), \
                 patch.object(rt, "push_branch", return_value=0):
                # include_code=False from the caller — auto_run must still
                # promote it to True because auto_commit=True.
                rc = rt.auto_run(
                    "T122", "claude",
                    auto_commit=True,
                    auto_push=False,
                    include_code=False,
                )

            assert rc == 0
            assert len(commit_calls) == 1
            assert commit_calls[0]["include_code"] is True, (
                "auto_commit must always promote include_code to True"
            )
            assert commit_calls[0]["workflow_step"] == "coder"
        finally:
            os.chdir(orig)


# ── 2. commit_ticket stages real code, excludes runtime ──────────────────────

def test_commit_ticket_stages_real_code_excludes_runtime():
    """Reproduce the T122 git status and verify that:
    - useful code paths end up in the final commit;
    - runtime.log / pyc / .pytest_cache / locks are unstaged before commit.
    """
    rt = _load_run_ticket()

    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T122", state="IMPLEMENTATION_REVIEW_NEEDED")

            staged_state = {
                "value": "\n".join([
                    # Real implementation files from T122
                    "apps/dashboard/src/api/tickets.js",
                    "apps/dashboard/src/pages/TicketDetailPage.jsx",
                    "apps/dashboard/src/components/AuditLog.jsx",
                    "services/control_api/main.py",
                    "services/control_api/models/schemas.py",
                    "services/control_api/routes/tickets.py",
                    # Workflow artifacts
                    "runs/T122/plan.md",
                    "runs/T122/implementation-output.md",
                    # Runtime garbage that git add -A also picked up
                    "runs/T122/runtime.log",
                    "runs/daemon.log",
                    "tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc",
                    ".pytest_cache/v/cache/lastfailed",
                    ".runtime/ai-dev-factory.sqlite",
                    "runs/T122/daemon.lock",
                ]) + "\n"
            }
            reset_paths: list[str] = []
            committed_message: list[str] = []

            def fake_run_command(args, cwd=None):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T122-work\n")
                if args == ["git", "diff", "--cached", "--name-only"]:
                    return _cp(staged_state["value"])
                if args[:2] == ["git", "add"]:
                    return _cp()
                if args[:3] == ["git", "reset", "HEAD"]:
                    p = args[-1]
                    reset_paths.append(p)
                    remaining = [
                        line for line in staged_state["value"].splitlines()
                        if line and line != p
                    ]
                    staged_state["value"] = "\n".join(remaining) + ("\n" if remaining else "")
                    return _cp()
                if args[:2] == ["git", "commit"]:
                    # find the message argument (after -m)
                    if "-m" in args:
                        committed_message.append(args[args.index("-m") + 1])
                    return _cp("ok")
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch.object(rt, "run_command", side_effect=fake_run_command):
                rc = rt.commit_ticket(
                    "T122",
                    None,
                    include_code=True,
                    workflow_step="coder",
                )

            assert rc == 0, "commit must succeed when useful code is dirty"

            # ── Runtime garbage MUST have been unstaged ──
            must_unstage = {
                "runs/T122/runtime.log",
                "runs/daemon.log",
                "tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc",
                ".pytest_cache/v/cache/lastfailed",
                ".runtime/ai-dev-factory.sqlite",
                "runs/T122/daemon.lock",
            }
            for p in must_unstage:
                assert p in reset_paths, f"runtime path {p!r} must be unstaged"

            # ── Real code MUST NOT have been unstaged ──
            must_keep = {
                "apps/dashboard/src/api/tickets.js",
                "apps/dashboard/src/pages/TicketDetailPage.jsx",
                "apps/dashboard/src/components/AuditLog.jsx",
                "services/control_api/main.py",
                "services/control_api/models/schemas.py",
                "services/control_api/routes/tickets.py",
            }
            for p in must_keep:
                assert p not in reset_paths, f"useful code {p!r} must NOT be unstaged"

            # ── Commit message must reference ticket id + useful scope ──
            assert committed_message, "commit must have been invoked"
            msg = committed_message[0]
            title = msg.splitlines()[0]
            assert "T122" in title
            # The scope must mention at least one of the two real components
            assert "dashboard" in title or "control-api" in title, (
                f"title should reference dashboard or control-api scope, got: {title!r}"
            )
            assert "refs T122" in msg
            # Some of the staged files must appear in the body
            assert "services/control_api/main.py" in msg
        finally:
            os.chdir(orig)


# ── 3. pre-sync hygiene: auto-commit useful dirty if auto_commit ─────────────

def test_presync_auto_commits_useful_dirty_when_auto_commit_enabled():
    """If real code is dirty when entering the sync step *and* ``auto_commit``
    is enabled, the daemon must auto-commit it before ``git pull --rebase``."""
    daemon = _load_run_daemon()

    real_dirty = [
        "apps/dashboard/src/api/tickets.js",
        "services/control_api/main.py",
    ]

    cp_calls: list[dict] = []

    def fake_checkpoint(ticket_id, message, **kwargs):
        cp_calls.append({"ticket_id": ticket_id, "message": message, **kwargs})

    pull_called = {"value": False}

    def fake_subprocess_run(args, **kwargs):
        if "pull" in args:
            pull_called["value"] = True
        return _cp(returncode=0)

    with patch.object(daemon, "_clean_runtime_before_sync", return_value=([], real_dirty)), \
         patch.object(daemon, "checkpoint_transition", side_effect=fake_checkpoint), \
         patch.object(daemon, "subprocess") as sp_mod:
        sp_mod.run.side_effect = fake_subprocess_run
        ok = daemon._sync_ticket_branch(
            "T122",
            "ticket/T122-work",
            cwd="/tmp/wt",
            auto_commit=True,
            auto_push=True,
        )

    assert ok is True
    assert len(cp_calls) == 1, "auto-commit must be triggered exactly once"
    call = cp_calls[0]
    assert call["include_code"] is True
    assert call["push"] is True
    assert "T122" in call["message"]
    assert "apps/dashboard/src/api/tickets.js" in call["message"]
    assert pull_called["value"], "rebase must run after auto-commit"


def test_presync_refuses_when_useful_dirty_and_no_auto_commit():
    """If real code is dirty and ``auto_commit`` is disabled, the daemon
    must refuse the rebase and skip the ticket. It must NOT silently
    modify the user's working tree."""
    daemon = _load_run_daemon()

    real_dirty = ["apps/dashboard/src/api/tickets.js"]

    pull_called = {"value": False}

    def fake_subprocess_run(args, **kwargs):
        if "pull" in args:
            pull_called["value"] = True
        return _cp(returncode=0)

    cp_calls: list[dict] = []

    def fake_checkpoint(*args, **kwargs):
        cp_calls.append(kwargs)

    with patch.object(daemon, "_clean_runtime_before_sync", return_value=([], real_dirty)), \
         patch.object(daemon, "checkpoint_transition", side_effect=fake_checkpoint), \
         patch.object(daemon, "subprocess") as sp_mod:
        sp_mod.run.side_effect = fake_subprocess_run
        ok = daemon._sync_ticket_branch(
            "T122",
            "ticket/T122-work",
            cwd="/tmp/wt",
            auto_commit=False,
            auto_push=False,
        )

    assert ok is False, "must refuse the rebase"
    assert cp_calls == [], "must NOT auto-commit when auto_commit is disabled"
    assert not pull_called["value"], "must NOT attempt git pull --rebase"


def test_presync_proceeds_when_only_runtime_dirty():
    """If only runtime garbage is dirty (now cleaned), the rebase proceeds
    normally — no auto-commit needed."""
    daemon = _load_run_daemon()

    cleaned = ["rm:runs/T122/runtime.log", "rm:tools/__pycache__/x.pyc"]

    pull_called = {"value": False}

    def fake_subprocess_run(args, **kwargs):
        if "pull" in args:
            pull_called["value"] = True
        return _cp(returncode=0)

    with patch.object(daemon, "_clean_runtime_before_sync", return_value=(cleaned, [])), \
         patch.object(daemon, "checkpoint_transition") as cp_mock, \
         patch.object(daemon, "subprocess") as sp_mod:
        sp_mod.run.side_effect = fake_subprocess_run
        ok = daemon._sync_ticket_branch(
            "T122",
            "ticket/T122-work",
            cwd="/tmp/wt",
            auto_commit=False,
            auto_push=False,
        )

    assert ok is True
    cp_mock.assert_not_called()
    assert pull_called["value"]


# ── 4. control-api daemon spawn includes --auto-include-code ─────────────────

def test_daemon_manager_start_passes_auto_include_code(tmp_path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.control_api.services import daemon_manager  # type: ignore

    captured: dict = {}

    class FakeProc:
        pid = 4321

    def fake_popen(args, **kwargs):
        captured["args"] = list(args)
        captured["env"] = kwargs.get("env")
        return FakeProc()

    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(daemon_manager, "_write_pid_file"):
        status_mock = MagicMock()
        status_mock.running = False
        gs.return_value = status_mock
        daemon_manager.start(tmp_path, "claude")

    assert "--auto-include-code" in captured["args"], (
        "control-api daemon spawn must pass --auto-include-code so the "
        "coder's real implementation files are committed"
    )
    # And the env still carries the no-bytecode flag from the previous fix
    assert captured["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
