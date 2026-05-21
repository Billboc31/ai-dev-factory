"""Tests for subprocess_runner — validation, subprocess calls, error handling."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services import subprocess_runner
from services.control_api.models.schemas import ActionResult


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.returncode = returncode
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


# ── ticket_id validation ──────────────────────────────────────────────────────

def test_invalid_ticket_id_raises(tmp_path):
    with pytest.raises(ValueError, match="invalid ticket_id"):
        subprocess_runner.run_next("INVALID", tmp_path)


def test_invalid_ticket_id_short_raises(tmp_path):
    with pytest.raises(ValueError, match="invalid ticket_id"):
        subprocess_runner.approve_plan("T1", tmp_path)


def test_valid_ticket_id_accepted(tmp_path):
    with patch("subprocess.run", return_value=_completed(0, "ok")):
        result = subprocess_runner.run_next("T001", tmp_path)
    assert isinstance(result, ActionResult)


# ── ok / fail result mapping ──────────────────────────────────────────────────

def test_subprocess_ok(tmp_path):
    with patch("subprocess.run", return_value=_completed(0, "success output")):
        result = subprocess_runner.approve_plan("T001", tmp_path)
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "success output"


def test_subprocess_fail(tmp_path):
    with patch("subprocess.run", return_value=_completed(1, stderr="error msg")):
        result = subprocess_runner.approve_plan("T001", tmp_path)
    assert result.ok is False
    assert result.returncode == 1
    assert result.stderr == "error msg"


def test_subprocess_oserror(tmp_path):
    with patch("subprocess.run", side_effect=OSError("file not found")):
        result = subprocess_runner.commit_ticket("T001", tmp_path)
    assert result.ok is False
    assert "file not found" in result.message
    assert result.returncode == -1


# ── no direct state.json mutation ────────────────────────────────────────────

def test_no_state_json_mutation(tmp_path):
    run_dir = tmp_path / "runs" / "T001"
    run_dir.mkdir(parents=True)
    state_path = run_dir / "state.json"
    state_data = {"ticket_id": "T001", "state": "PLAN_APPROVED"}
    state_path.write_text(json.dumps(state_data))
    mtime_before = state_path.stat().st_mtime

    with patch("subprocess.run", return_value=_completed(0)):
        subprocess_runner.approve_plan("T001", tmp_path)

    mtime_after = state_path.stat().st_mtime
    assert mtime_before == mtime_after, "subprocess_runner must not mutate state.json"


# ── intake endpoint ───────────────────────────────────────────────────────────

def test_issue_intake_calls_script(tmp_path):
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        result = subprocess_runner.run_issue_intake(42, tmp_path)
    assert result.ok is True
    call_args = mock_run.call_args[0][0]
    assert "run_issue_intake.py" in " ".join(str(a) for a in call_args)
    assert "42" in call_args


# ── commit / checkpoint include-code ─────────────────────────────────────────

def test_commit_ticket_includes_include_code_flag(tmp_path):
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        subprocess_runner.commit_ticket("T001", tmp_path)
    args_str = " ".join(str(a) for a in mock_run.call_args[0][0])
    assert "--commit" in args_str
    assert "--include-code" in args_str


def test_checkpoint_ticket_uses_commit_with_include_code(tmp_path):
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        subprocess_runner.checkpoint_ticket("T001", tmp_path)
    args_str = " ".join(str(a) for a in mock_run.call_args[0][0])
    assert "--commit" in args_str
    assert "--include-code" in args_str


def test_archive_ticket_calls_archive_daemon_flag(tmp_path):
    with patch("subprocess.run", return_value=_completed(0)) as mock_run:
        result = subprocess_runner.archive_ticket("T001", tmp_path)
    assert result.ok is True
    args_str = " ".join(str(a) for a in mock_run.call_args[0][0])
    assert "--archive-daemon" in args_str
    assert "T001" in args_str


# ── daemon action endpoints ───────────────────────────────────────────────────

def test_daemon_start_stop(tmp_path):
    (tmp_path / "runs").mkdir()
    from services.control_api.services import daemon_manager

    # Stub the preflight check so this test can focus on Popen/stop wiring.
    facts = {
        "project_root": str(tmp_path),
        "cwd": str(tmp_path),
        "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
        "worktrees_dir": "/wt",
        "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
        "runtime_root": "<unset>",
        "python": "/usr/bin/python3",
        "git_path": "/usr/bin/git",
        "gh_path": "/usr/bin/gh",
    }
    with patch("subprocess.Popen") as mock_popen, \
         patch.object(daemon_manager, "check_environment", return_value=(True, [], facts)):
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc

        result = daemon_manager.start(tmp_path, "echo ok")
        assert result.ok is True
        assert "99999" in result.message

    with patch("os.kill") as mock_kill:
        result = daemon_manager.stop(tmp_path)
        assert result.ok is True
        # os.kill is called twice: once to probe liveness (signal 0), once for SIGTERM
        assert mock_kill.call_count == 2


def test_daemon_start_already_running(tmp_path):
    import os
    (tmp_path / "runs").mkdir()
    pid = os.getpid()
    (tmp_path / "runs" / "daemon.pid").write_text(json.dumps({"pid": pid, "started_at": "2026-01-01T00:00:00Z"}))

    from services.control_api.services import daemon_manager
    result = daemon_manager.start(tmp_path, "echo ok")
    assert result.ok is False
    assert "already running" in result.message


def test_daemon_stop_not_running(tmp_path):
    (tmp_path / "runs").mkdir()
    from services.control_api.services import daemon_manager
    result = daemon_manager.stop(tmp_path)
    assert result.ok is False
    assert "not running" in result.message


# ── daemon get_activity ───────────────────────────────────────────────────────

def test_get_activity_no_log(tmp_path):
    (tmp_path / "runs").mkdir()
    from services.control_api.services import daemon_manager
    assert daemon_manager.get_activity(tmp_path) == []


def test_get_activity_with_log(tmp_path):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "daemon.log").write_text("line1\nline2\nline3\n")
    from services.control_api.services import daemon_manager
    lines = daemon_manager.get_activity(tmp_path, lines=2)
    assert lines == ["line2", "line3"]


def test_get_activity_filters_empty_lines(tmp_path):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "daemon.log").write_text("line1\n\nline3\n")
    from services.control_api.services import daemon_manager
    lines = daemon_manager.get_activity(tmp_path)
    assert "" not in lines
    assert len(lines) == 2


def test_get_status_includes_current_ticket(tmp_path):
    import os
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ticket_dir = runs_dir / "T030"
    ticket_dir.mkdir()
    (ticket_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T030", "state": "CODER_RUNNING"})
    )
    pid = os.getpid()
    (runs_dir / "daemon.pid").write_text(json.dumps({"pid": pid, "started_at": "2026-01-01T00:00:00Z"}))
    from services.control_api.services import daemon_manager
    status = daemon_manager.get_status(tmp_path)
    assert status.running is True
    assert status.current_ticket == "T030"


def test_get_status_current_ticket_none_when_no_running_ticket(tmp_path):
    import os
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ticket_dir = runs_dir / "T001"
    ticket_dir.mkdir()
    (ticket_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED"})
    )
    pid = os.getpid()
    (runs_dir / "daemon.pid").write_text(json.dumps({"pid": pid, "started_at": "2026-01-01T00:00:00Z"}))
    from services.control_api.services import daemon_manager
    status = daemon_manager.get_status(tmp_path)
    assert status.current_ticket is None
