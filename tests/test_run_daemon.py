"""Tests for T020 — local workflow daemon."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

import run_daemon
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
    reap_completed_workers,
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
    mock_launch.assert_called_once_with(
        "T001", "test-cmd", False, runs,
        worktrees_dir=None, auto_commit=False, auto_push=False, auto_include_code=False,
        state_dir=runs,
    )


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


def test_run_once_skips_launch_when_eligibility_not_ready(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    _write_state(runs, "T003", "INIT")
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "off")
    monkeypatch.setattr(
        run_daemon,
        "_launch_blocked_by_eligibility",
        lambda *_a, **_k: "Dependency T001 not merged",
    )
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


def _launch_preflight_ok(*, branch: str = "ticket/T001"):
    return patch.multiple(
        "run_daemon",
        _sync_ticket_branch=MagicMock(return_value=True),
        _ensure_clean_working_tree=MagicMock(return_value=True),
        _get_current_branch=MagicMock(return_value=branch),
    )


# ── launch_ticket ─────────────────────────────────────────────────────────────

def test_launch_ticket_dry_run_does_not_call_subprocess(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon._spawn_worker_process") as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=True, runs_dir=runs)
    mock_spawn.assert_not_called()


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
        with patch("run_daemon._spawn_worker_process") as mock_spawn:
            launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    mock_spawn.assert_not_called()


def test_launch_ticket_releases_lock_after_reap(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    proc = MagicMock()
    proc.pid = 4242
    proc.poll.return_value = None
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, state_dir=state_dir)
    assert _lock_path(run_dir).exists()
    proc.poll.return_value = 0
    reap_completed_workers(state_dir)
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


def test_resolve_repo_root_uses_explicit_project_root(tmp_path, monkeypatch):
    from argparse import Namespace
    from run_daemon import _resolve_repo_root

    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    repo = tmp_path / "managed"
    repo.mkdir()
    subprocess_run = __import__("subprocess").run
    subprocess_run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "config", "user.email", "t@e.com"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "config", "user.name", "T"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
    subprocess_run(["git", "add", "-A"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    args = Namespace(project_root=str(repo))
    assert _resolve_repo_root(args) == repo.resolve()


# ── dispatcher-aware scheduling ───────────────────────────────────────────────

def test_run_once_legacy_when_dispatcher_off(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    _write_state(runs, "T002", "INIT")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "off")
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")

    spy_select = MagicMock()
    monkeypatch.setattr(run_daemon, "_select_tickets_via_dispatcher", spy_select)

    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)

    assert mock_launch.call_count == 2
    called_ids = [c.args[0] for c in mock_launch.call_args_list]
    assert called_ids == ["T001", "T002"]
    spy_select.assert_not_called()
    assert "scheduling: legacy (dispatcher=off)" in capsys.readouterr().out


def test_run_once_uses_dispatcher_when_enabled(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    # Legacy scan would sort as T001, T002 — dispatcher must override the order.
    _write_state(runs, "T001", "PLAN_APPROVED")
    _write_state(runs, "T002", "PLAN_APPROVED")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "advisory")
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")
    monkeypatch.setattr(
        run_daemon,
        "_get_recommended_tickets",
        lambda _db, _root, **_kw: {
            "mode": "advisory",
            "recommendations": [
                {"ticket_id": "T002", "rank": 1, "score": 80},
                {"ticket_id": "T001", "rank": 2, "score": 70},
            ],
            "blocked": [],
        },
    )

    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)

    called_ids = [c.args[0] for c in mock_launch.call_args_list]
    assert called_ids == ["T002", "T001"]
    assert "scheduling: dispatcher (mode=advisory)" in capsys.readouterr().out


def test_run_once_launches_nothing_when_dispatcher_empty(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "advisory")
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")
    monkeypatch.setattr(
        run_daemon,
        "_get_recommended_tickets",
        lambda _db, _root, **_kw: {"mode": "advisory", "recommendations": [], "blocked": []},
    )

    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)

    mock_launch.assert_not_called()
    out = capsys.readouterr().out
    assert "scheduling: dispatcher (mode=advisory)" in out
    assert "dispatcher returned no runnable tickets; launching nothing" in out


def test_run_once_launches_nothing_when_dispatcher_raises(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "manual")
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("dispatcher unavailable")

    monkeypatch.setattr(run_daemon, "_get_recommended_tickets", _boom)

    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)

    mock_launch.assert_not_called()
    out = capsys.readouterr().out
    assert "scheduling: dispatcher (mode=manual)" in out
    assert "dispatcher get_recommended_tickets failed" in out
    assert "dispatcher returned no runnable tickets; launching nothing" in out


def test_run_once_dispatcher_skips_when_state_not_auto_runnable(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    # Dispatcher recommends a ticket whose state is not in AUTO_RUNNABLE_STATES.
    _write_state(runs, "T001", "TEST_COMPLETE")
    _write_state(runs, "T002", "PLAN_APPROVED")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: "advisory")
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")
    monkeypatch.setattr(
        run_daemon,
        "_get_recommended_tickets",
        lambda _db, _root, **_kw: {
            "mode": "advisory",
            "recommendations": [
                {"ticket_id": "T001", "rank": 1, "score": 80},
                {"ticket_id": "T002", "rank": 2, "score": 70},
            ],
            "blocked": [],
        },
    )

    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)

    called_ids = [c.args[0] for c in mock_launch.call_args_list]
    assert called_ids == ["T002"]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("off", "scheduling: legacy (dispatcher=off)"),
        ("advisory", "scheduling: dispatcher (mode=advisory)"),
        ("manual", "scheduling: dispatcher (mode=manual)"),
        ("auto", "scheduling: dispatcher (mode=auto)"),
    ],
)
def test_run_once_logs_active_strategy(tmp_path, monkeypatch, capsys, mode, expected):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")

    import run_daemon
    monkeypatch.setattr(run_daemon, "_get_dispatcher_mode", lambda _db: mode)
    monkeypatch.setattr(run_daemon, "_ensure_db", lambda: tmp_path / "fake.sqlite")
    monkeypatch.setattr(
        run_daemon,
        "_get_recommended_tickets",
        lambda _db, _root, **_kw: {
            "mode": mode,
            "recommendations": [{"ticket_id": "T001", "rank": 1, "score": 80}],
            "blocked": [],
        },
    )

    with patch("run_daemon.launch_ticket"):
        run_once("test-cmd", False, runs)

    assert expected in capsys.readouterr().out


def test_dispatcher_helper_returns_off_when_db_missing():
    from run_daemon import _dispatcher_enabled
    enabled, mode = _dispatcher_enabled(None)
    assert enabled is False
    assert mode == "off"


def test_resolve_repo_root_uses_cwd_when_runtime_root_set(tmp_path, monkeypatch):
    from argparse import Namespace
    from run_daemon import _resolve_repo_root

    repo = tmp_path / "managed"
    repo.mkdir()
    subprocess_run = __import__("subprocess").run
    subprocess_run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "config", "user.email", "t@e.com"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "config", "user.name", "T"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
    subprocess_run(["git", "add", "-A"], cwd=repo, capture_output=True, check=True)
    subprocess_run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.chdir(repo)
    args = Namespace(project_root=None)
    assert _resolve_repo_root(args) == repo.resolve()
