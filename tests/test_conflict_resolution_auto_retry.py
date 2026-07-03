"""Tests for daemon auto-retry budget before human conflict resolution."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

import conflict_resolution_eligibility as cre
import run_daemon


def _run_dir(tmp_path: Path, state: str = "CONFLICT_RESOLUTION_FAILED") -> Path:
    run_dir = tmp_path / "runs" / "T011"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T011", "state": state}, indent=2),
        encoding="utf-8",
    )
    return run_dir


def test_conflict_auto_runs_default_zero():
    assert cre.conflict_resolution_auto_runs({}) == 0
    assert cre.conflict_resolution_auto_retries_exhausted({}) is False


def test_record_and_exhaust_conflict_auto_runs():
    state: dict = {}
    state, n1 = cre.record_conflict_resolution_auto_run(state)
    assert n1 == 1
    state, n2 = cre.record_conflict_resolution_auto_run(state)
    assert n2 == 2
    assert cre.conflict_resolution_auto_retries_exhausted(state) is False
    state, n3 = cre.record_conflict_resolution_auto_run(state)
    assert n3 == 3
    assert cre.conflict_resolution_auto_retries_exhausted(state) is True


def test_clear_conflict_retry_preserves_other_keys():
    state = {
        "attempts": 2,
        "conflict_resolution_runs": 3,
        "conflict_resolution_auto_stopped": True,
        "conflict_resolution_stop_reason": "max",
    }
    cleared = cre.clear_conflict_resolution_retry(state)
    assert cleared == {"attempts": 2}


def test_reset_conflict_resolution_auto_retry_file(tmp_path):
    run_dir = _run_dir(tmp_path)
    retry_path = run_dir / cre.RETRY_STATE_FILENAME
    retry_path.write_text(
        json.dumps(
            {
                "attempts": 1,
                "conflict_resolution_runs": 2,
                "conflict_resolution_auto_stopped": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    cre.reset_conflict_resolution_auto_retry(run_dir)
    data = json.loads(retry_path.read_text(encoding="utf-8"))
    assert data == {"attempts": 1}


def test_detect_pr_conflict_resets_auto_retry(tmp_path):
    run_dir = _run_dir(tmp_path, state="TEST_COMPLETE")
    retry_path = run_dir / cre.RETRY_STATE_FILENAME
    retry_path.write_text(
        json.dumps({"conflict_resolution_runs": 3, "conflict_resolution_auto_stopped": True}),
        encoding="utf-8",
    )

    def _mock_gh(*_args, **_kwargs):
        return MagicMock(
            returncode=0,
            stdout=json.dumps({"mergeable": "CONFLICTING"}),
            stderr="",
        )

    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=[_mock_gh(), _mock_gh()]):
        from ticket_pr_lifecycle import detect_pr_conflict

        assert detect_pr_conflict("T011", 27, run_dir) is True

    if retry_path.exists():
        data = json.loads(retry_path.read_text(encoding="utf-8"))
        assert "conflict_resolution_runs" not in data
        assert "conflict_resolution_auto_stopped" not in data


def test_maybe_auto_launch_increments_run_counter(tmp_path):
    run_dir = _run_dir(tmp_path, state="CONFLICT_RESOLUTION_NEEDED")
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    db = tmp_path / "proj.sqlite"
    db.touch()

    proc = MagicMock(pid=4242)
    with patch(
        "execution_rules_engine.is_human_conflict_resolution_approval_required",
        return_value=False,
    ), \
         patch("run_daemon._acquire_lock", return_value=True), \
         patch("run_daemon._spawn_worker_process", return_value=proc) as mock_spawn, \
         patch("run_daemon._set_lock_holder_pid"):
        assert run_daemon._maybe_auto_launch_conflict_resolution(
            "T011", "echo agent", False, run_dir, wt, "test-ai-dev", db,
        ) is True

    mock_spawn.assert_called_once()
    retry = json.loads((run_dir / run_daemon.RETRY_STATE_FILENAME).read_text())
    assert retry["conflict_resolution_runs"] == 1


def test_maybe_auto_launch_stops_after_max_runs(tmp_path):
    run_dir = _run_dir(tmp_path)
    (run_dir / run_daemon.RETRY_STATE_FILENAME).write_text(
        json.dumps({"conflict_resolution_runs": cre.MAX_CONFLICT_RESOLVER_AUTO_RUNS}),
        encoding="utf-8",
    )
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    db = tmp_path / "proj.sqlite"
    db.touch()

    with patch(
        "execution_rules_engine.is_human_conflict_resolution_approval_required",
        return_value=False,
    ), \
         patch("run_daemon._acquire_lock") as mock_lock, \
         patch("run_daemon._spawn_worker_process") as mock_spawn:
        assert run_daemon._maybe_auto_launch_conflict_resolution(
            "T011", "echo agent", False, run_dir, wt, "test-ai-dev", db,
        ) is False

    mock_lock.assert_not_called()
    mock_spawn.assert_not_called()
    retry = json.loads((run_dir / run_daemon.RETRY_STATE_FILENAME).read_text())
    assert retry["conflict_resolution_auto_stopped"] is True
