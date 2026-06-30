"""Tests for background worker launch and reap in run_daemon."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

import run_daemon
from run_daemon import (
    _lock_path,
    launch_ticket,
    reap_completed_workers,
)


def _launch_preflight_ok(*, branch: str = "ticket/T001"):
    return patch.multiple(
        "run_daemon",
        _sync_ticket_branch=MagicMock(return_value=True),
        _ensure_clean_working_tree=MagicMock(return_value=True),
        _get_current_branch=MagicMock(return_value=branch),
    )


def _write_state(runs: Path, ticket_id: str, state: str) -> Path:
    run_dir = runs / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    return run_dir


def _mock_popen(*, pid: int = 4242, running: bool = True, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.pid = pid
    if running:
        proc.poll.return_value = None
    else:
        proc.poll.return_value = returncode
        proc.returncode = returncode
    return proc


def _clear_workers() -> None:
    run_daemon._ACTIVE_WORKERS.clear()


def test_launch_ticket_starts_background_worker_and_keeps_lock(tmp_path):
    runs = tmp_path / "runs"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    proc = _mock_popen()
    _clear_workers()

    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, state_dir=state_dir)

    mock_spawn.assert_called_once()
    assert _lock_path(run_dir).exists()
    assert "T001" in run_daemon._ACTIVE_WORKERS
    workers = run_daemon._load_workers_registry(state_dir)
    assert workers["T001"]["pid"] == 4242


def test_reap_completed_workers_releases_lock_and_unregisters(tmp_path):
    runs = tmp_path / "runs"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    proc = _mock_popen(running=False, returncode=0)
    _lock_path(run_dir).write_text(json.dumps({"pid": proc.pid}), encoding="utf-8")
    run_daemon._ACTIVE_WORKERS["T001"] = {"proc": proc, "run_dir": run_dir}
    run_daemon._register_worker(state_dir, "T001", "ticket/T001", "", pid=proc.pid)

    reap_completed_workers(state_dir)

    assert "T001" not in run_daemon._ACTIVE_WORKERS
    assert not _lock_path(run_dir).exists()
    assert "T001" not in run_daemon._load_workers_registry(state_dir)


def test_reap_applies_retry_policy_on_failure(tmp_path):
    runs = tmp_path / "runs"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: quota_exceeded (rc=1)\n",
        encoding="utf-8",
    )
    proc = _mock_popen(running=False, returncode=1)
    run_daemon._ACTIVE_WORKERS["T001"] = {"proc": proc, "run_dir": run_dir}
    _clear_workers()
    run_daemon._ACTIVE_WORKERS["T001"] = {"proc": proc, "run_dir": run_dir}

    reap_completed_workers(state_dir)

    retry_path = run_dir / run_daemon.RETRY_STATE_FILENAME
    assert retry_path.exists()
    state = json.loads(retry_path.read_text(encoding="utf-8"))
    assert state.get("failure_class") == "quota_exceeded"


def test_count_live_workers_uses_child_pid(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    run_daemon._register_worker(state_dir, "T001", "ticket/T001", "", pid=99999)
    with patch("run_daemon._is_pid_alive", return_value=True):
        assert run_daemon._count_live_workers(state_dir) == 1
    with patch("run_daemon._is_pid_alive", return_value=False):
        assert run_daemon._count_live_workers(state_dir) == 0
