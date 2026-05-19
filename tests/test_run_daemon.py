"""Tests for T020 — local workflow daemon."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    AUTO_RUNNABLE_STATES,
    HUMAN_GATE_STATES,
    _acquire_lock,
    _check_runtime_clone,
    _is_pid_alive,
    _lock_path,
    _release_lock,
    build_run_ticket_command,
    handle_test_complete,
    launch_ticket,
    main,
    run_once,
    scan_tickets,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_state(runs_dir: Path, ticket_id: str, state: str) -> Path:
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    return run_dir


# ── state constants ───────────────────────────────────────────────────────────

def test_auto_runnable_states_contains_all_six():
    assert AUTO_RUNNABLE_STATES == frozenset({
        "INIT",
        "PLAN_APPROVED",
        "IMPLEMENTATION_REVIEW_NEEDED",
        "IMPLEMENTATION_APPROVED",
        "PLAN_FIX_REQUIRED",
        "IMPLEMENTATION_FIX_REQUIRED",
    })


def test_human_gate_states_contains_expected():
    assert "PLAN_REVIEW_NEEDED" in HUMAN_GATE_STATES
    assert "TEST_COMPLETE" in HUMAN_GATE_STATES


def test_auto_runnable_and_human_gate_are_disjoint():
    assert AUTO_RUNNABLE_STATES.isdisjoint(HUMAN_GATE_STATES)


# ── scan_tickets ──────────────────────────────────────────────────────────────

def test_scan_tickets_returns_ticket_and_state(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    result = scan_tickets(runs)
    assert result == [("T001", "PLAN_APPROVED")]


def test_scan_tickets_skips_corrupted_state(tmp_path, capsys):
    runs = tmp_path / "runs"
    run_dir = runs / "T002"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("not json", encoding="utf-8")
    result = scan_tickets(runs)
    assert result == []
    assert "T002" in capsys.readouterr().out


def test_scan_tickets_skips_empty_state_field(tmp_path):
    runs = tmp_path / "runs"
    run_dir = runs / "T003"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T003", "state": ""}), encoding="utf-8"
    )
    result = scan_tickets(runs)
    assert result == []


def test_scan_tickets_returns_multiple_sorted(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T002", "INIT")
    _write_state(runs, "T001", "PLAN_APPROVED")
    result = scan_tickets(runs)
    assert [t for t, _ in result] == ["T001", "T002"]


def test_scan_tickets_skips_daemon_archived(tmp_path):
    runs = tmp_path / "runs"
    run_dir = runs / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE", "daemon_archived": True}),
        encoding="utf-8",
    )
    result = scan_tickets(runs)
    assert result == []


def test_scan_tickets_skips_daemon_archived_logs_message(tmp_path, capsys):
    runs = tmp_path / "runs"
    run_dir = runs / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE", "daemon_archived": True}),
        encoding="utf-8",
    )
    scan_tickets(runs)
    assert "daemon_archived=true" in capsys.readouterr().out


def test_run_once_skips_test_complete_when_issue_closed(tmp_path):
    runs = tmp_path / "runs"
    run_dir = runs / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE", "issue_closed": True}),
        encoding="utf-8",
    )
    with patch("run_daemon.handle_test_complete") as mock_handle:
        run_once("test-cmd", False, runs)
    mock_handle.assert_not_called()


def test_run_once_skips_test_complete_when_pr_skipped_no_diff(tmp_path):
    runs = tmp_path / "runs"
    run_dir = runs / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE", "pr_skipped_no_diff": True}),
        encoding="utf-8",
    )
    with patch("run_daemon.handle_test_complete") as mock_handle:
        run_once("test-cmd", False, runs)
    mock_handle.assert_not_called()


# ── run_once ──────────────────────────────────────────────────────────────────

def test_run_once_calls_launch_for_auto_runnable_state(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_called_once_with("T001", "test-cmd", False, runs, worktrees_dir=None, auto_commit=False, auto_push=False, auto_include_code=False)


def test_run_once_skips_human_gate_state(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_REVIEW_NEEDED")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_not_called()


def test_run_once_skips_unknown_state(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "SOME_UNKNOWN_STATE")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_not_called()


def test_run_once_logs_human_gate_skip(tmp_path, capsys):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "TEST_COMPLETE")
    with patch("run_daemon.launch_ticket"):
        run_once("test-cmd", False, runs)
    assert "human gate" in capsys.readouterr().out


def test_run_once_logs_no_tickets_when_empty(tmp_path, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    run_once("test-cmd", False, runs)
    assert "no tickets found" in capsys.readouterr().out


# ── lock management ───────────────────────────────────────────────────────────

def test_acquire_lock_creates_lock_file(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    result = _acquire_lock(run_dir)
    assert result is True
    assert _lock_path(run_dir).exists()
    data = json.loads(_lock_path(run_dir).read_text())
    assert data["pid"] == os.getpid()


def test_acquire_lock_returns_false_when_live_pid_holds_lock(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _lock_path(run_dir).write_text(
        json.dumps({"pid": os.getpid(), "created_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    with patch("run_daemon._is_pid_alive", return_value=True):
        result = _acquire_lock(run_dir)
    assert result is False


def test_acquire_lock_cleans_stale_lock_and_acquires(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _lock_path(run_dir).write_text(
        json.dumps({"pid": 99999999, "created_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    with patch("run_daemon._is_pid_alive", return_value=False):
        result = _acquire_lock(run_dir)
    assert result is True
    data = json.loads(_lock_path(run_dir).read_text())
    assert data["pid"] == os.getpid()


def test_release_lock_removes_file(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _lock_path(run_dir).write_text("{}", encoding="utf-8")
    _release_lock(run_dir)
    assert not _lock_path(run_dir).exists()


def test_release_lock_is_idempotent(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _release_lock(run_dir)  # no file — should not raise


# ── launch_ticket ─────────────────────────────────────────────────────────────

def test_launch_ticket_dry_run_does_not_call_subprocess(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon.subprocess.run") as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=True, runs_dir=runs)
    mock_sub.assert_not_called()


def test_launch_ticket_dry_run_logs_action(tmp_path, capsys):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    launch_ticket("T001", "test-cmd", dry_run=True, runs_dir=runs)
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "T001" in out


def test_launch_ticket_blocked_by_live_lock_does_not_launch(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    _lock_path(run_dir).write_text(
        json.dumps({"pid": os.getpid(), "created_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    with patch("run_daemon._is_pid_alive", return_value=True):
        with patch("run_daemon.subprocess.run") as mock_sub:
            launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    mock_sub.assert_not_called()


def test_launch_ticket_releases_lock_after_run(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    assert not _lock_path(run_dir).exists()


# ── _check_runtime_clone ──────────────────────────────────────────────────────

def test_check_runtime_clone_returns_true_when_sentinel_exists(tmp_path, monkeypatch):
    sentinel = tmp_path / ".ai-dev-factory-runtime"
    sentinel.touch()
    import run_daemon
    monkeypatch.setattr(run_daemon, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    assert _check_runtime_clone() is True


def test_check_runtime_clone_returns_true_when_env_var_set(tmp_path, monkeypatch):
    import run_daemon
    monkeypatch.setattr(run_daemon, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", "/runtime/ai-dev-factory")
    assert _check_runtime_clone() is True


def test_check_runtime_clone_returns_false_when_neither(tmp_path, monkeypatch):
    import run_daemon
    monkeypatch.setattr(run_daemon, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    assert _check_runtime_clone() is False


def test_check_runtime_clone_prints_error_when_neither(tmp_path, monkeypatch, capsys):
    import run_daemon
    monkeypatch.setattr(run_daemon, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    _check_runtime_clone()
    assert "runtime clone" in capsys.readouterr().err


# ── main / CLI ────────────────────────────────────────────────────────────────

def test_main_once_returns_zero(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    with patch("run_daemon._check_runtime_clone", return_value=True):
        rc = main(["--exec-cmd", "test-cmd", "--once", "--runs-dir", str(runs)])
    assert rc == 0


def test_main_returns_2_when_runs_dir_missing(tmp_path):
    with patch("run_daemon._check_runtime_clone", return_value=True):
        rc = main(["--exec-cmd", "test-cmd", "--once", "--runs-dir", str(tmp_path / "nonexistent")])
    assert rc == 2


def test_main_returns_2_when_not_runtime_clone(tmp_path, monkeypatch):
    import run_daemon
    monkeypatch.setattr(run_daemon, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    runs = tmp_path / "runs"
    runs.mkdir()
    rc = main(["--exec-cmd", "test-cmd", "--once", "--runs-dir", str(runs)])
    assert rc == 2


# ── build_run_ticket_command ──────────────────────────────────────────────────

def test_build_run_ticket_command_positional_structure():
    cmd = build_run_ticket_command("T032", "claude --dangerously-skip-permissions")
    assert cmd[2] == "T032"
    assert "--auto" in cmd
    assert "--exec-cmd" in cmd


def test_build_run_ticket_command_exec_cmd_not_split():
    cmd = build_run_ticket_command("T032", "claude --dangerously-skip-permissions")
    idx = cmd.index("--exec-cmd")
    assert cmd[idx + 1] == "claude --dangerously-skip-permissions"
    assert "--dangerously-skip-permissions" not in cmd


def test_build_run_ticket_command_optional_flags_included():
    cmd = build_run_ticket_command("T032", "test", auto_commit=True, auto_push=True, auto_include_code=True)
    assert "--auto-commit" in cmd
    assert "--auto-push" in cmd
    assert "--auto-include-code" in cmd


def test_build_run_ticket_command_optional_flags_absent_by_default():
    cmd = build_run_ticket_command("T032", "test")
    assert "--auto-commit" not in cmd
    assert "--auto-push" not in cmd
    assert "--auto-include-code" not in cmd
