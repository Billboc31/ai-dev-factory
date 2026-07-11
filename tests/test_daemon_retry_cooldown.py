"""Tests for T025 — daemon retry and cooldown policy."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    _apply_retry_policy,
    _clear_retry_state,
    _is_blocked_by_retry,
    _load_retry_state,
    _read_last_failure_class,
    _retry_state_path,
    _save_retry_state,
    launch_ticket,
    reap_completed_workers,
    run_once,
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


def _future_iso(seconds: int = 3600) -> str:
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


def _past_iso(seconds: int = 3600) -> str:
    until = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── _read_last_failure_class ──────────────────────────────────────────────────

def test_read_last_failure_class_no_log(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    assert _read_last_failure_class(run_dir) is None


def test_read_last_failure_class_no_failure_lines(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run start: state=PLAN_APPROVED\n",
        encoding="utf-8",
    )
    assert _read_last_failure_class(run_dir) is None


def test_read_last_failure_class_returns_last_match(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: provider_error (rc=1)\n"
        "[2026-01-01T00:01:00Z] auto-run: runtime failure: quota_exceeded (rc=1)\n",
        encoding="utf-8",
    )
    assert _read_last_failure_class(run_dir) == "quota_exceeded"


def test_read_last_failure_class_single_line(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: write_permission_missing (rc=0)\n",
        encoding="utf-8",
    )
    assert _read_last_failure_class(run_dir) == "write_permission_missing"


# ── _load_retry_state / _save_retry_state / _clear_retry_state ───────────────

def test_load_retry_state_returns_empty_when_no_file(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    assert _load_retry_state(run_dir) == {}


def test_save_and_load_retry_state_round_trip(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    state = {"failure_class": "quota_exceeded", "retry_count": 2, "stopped": False}
    _save_retry_state(run_dir, state)
    assert _load_retry_state(run_dir) == state


def test_clear_retry_state_removes_file(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _save_retry_state(run_dir, {"stopped": True})
    _clear_retry_state(run_dir)
    assert not _retry_state_path(run_dir).exists()


def test_clear_retry_state_is_idempotent(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    _clear_retry_state(run_dir)  # no file — must not raise


# ── _apply_retry_policy — stop policies ──────────────────────────────────────

def test_apply_retry_policy_write_permission_missing_stops(tmp_path):
    result = _apply_retry_policy("T001", "write_permission_missing", {})
    assert result["stopped"] is True
    assert result["stop_reason"] == "write_permission_missing"


def test_apply_retry_policy_unknown_stops(tmp_path):
    result = _apply_retry_policy("T001", "unknown", {})
    assert result["stopped"] is True
    assert result["stop_reason"] == "unknown"


def test_apply_retry_policy_unrecognized_class_stops(tmp_path):
    result = _apply_retry_policy("T001", "totally_made_up", {})
    assert result["stopped"] is True


# ── _apply_retry_policy — cooldown policy ────────────────────────────────────

def test_apply_retry_policy_quota_exceeded_sets_cooldown(tmp_path):
    result = _apply_retry_policy("T001", "quota_exceeded", {})
    assert "cooldown_until" in result
    assert result.get("stopped") is not True
    assert result["failure_class"] == "quota_exceeded"


def test_apply_retry_policy_quota_exceeded_uses_provider_reset_when_available():
    reset_at = _future_iso(1800)
    result = _apply_retry_policy(
        "T001",
        "quota_exceeded",
        {"quota_reset_at": reset_at},
    )
    assert result["cooldown_until"] == reset_at


def test_apply_retry_policy_quota_exceeded_cooldown_roughly_one_hour():
    result = _apply_retry_policy("T001", "quota_exceeded", {})
    until = datetime.datetime.strptime(result["cooldown_until"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = (until - now).total_seconds()
    assert 3590 <= delta <= 3610


# ── _apply_retry_policy — exponential policy ─────────────────────────────────

def test_apply_retry_policy_provider_error_first_retry_increments_count():
    result = _apply_retry_policy("T001", "provider_error", {})
    assert result["retry_count"] == 1
    assert "cooldown_until" in result
    assert result.get("stopped") is not True


def test_apply_retry_policy_provider_error_delay_doubles():
    state_after_1 = _apply_retry_policy("T001", "provider_error", {})
    state_after_2 = _apply_retry_policy("T001", "provider_error", state_after_1)
    until1 = datetime.datetime.strptime(state_after_1["cooldown_until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    until2 = datetime.datetime.strptime(state_after_2["cooldown_until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    delay1 = (until1 - now).total_seconds()
    delay2 = (until2 - now).total_seconds()
    assert delay2 > delay1 * 1.5


def test_apply_retry_policy_provider_error_after_max_retries_sets_long_cooldown():
    state = {"retry_count": 5}
    result = _apply_retry_policy("T001", "provider_error", state)
    assert result.get("stopped") is not True
    until = datetime.datetime.strptime(result["cooldown_until"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = (until - now).total_seconds()
    assert delta >= 3590


def test_apply_retry_policy_process_crashed_same_as_provider_error():
    r1 = _apply_retry_policy("T001", "process_crashed", {})
    r2 = _apply_retry_policy("T001", "provider_error", {})
    assert r1["retry_count"] == r2["retry_count"]
    assert r1.get("stopped") == r2.get("stopped")


# ── _apply_retry_policy — fixed_delay policy ─────────────────────────────────

def test_apply_retry_policy_planner_invalid_uses_fixed_delay():
    """T118 follow-up: planner validation failures must be classified and bounded."""
    result = _apply_retry_policy("T001", "planner_invalid", {})
    assert result["retry_count"] == 1
    assert "cooldown_until" in result
    assert result.get("stopped") is not True
    assert result["failure_class"] == "planner_invalid"


def test_apply_retry_policy_planner_invalid_stops_after_max_retries():
    state = {"retry_count": 3}
    result = _apply_retry_policy("T001", "planner_invalid", state)
    assert result["stopped"] is True
    assert "planner_invalid" in result["stop_reason"]


def test_apply_retry_policy_dirty_tree_uses_fixed_delay():
    """T118 follow-up: dirty-tree gate failures must be classified and bounded."""
    result = _apply_retry_policy("T001", "dirty_tree", {})
    assert result["retry_count"] == 1
    assert "cooldown_until" in result
    assert result.get("stopped") is not True
    assert result["failure_class"] == "dirty_tree"


def test_apply_retry_policy_dirty_tree_stops_after_max_retries():
    state = {"retry_count": 3}
    result = _apply_retry_policy("T001", "dirty_tree", state)
    assert result["stopped"] is True
    assert "dirty_tree" in result["stop_reason"]


def test_apply_retry_policy_process_failed_first_retry_sets_delay():
    result = _apply_retry_policy("T001", "process_failed", {})
    assert result["retry_count"] == 1
    assert "cooldown_until" in result
    assert result.get("stopped") is not True


def test_apply_retry_policy_process_failed_after_max_retries_stops():
    state = {"retry_count": 3}
    result = _apply_retry_policy("T001", "process_failed", state)
    assert result["stopped"] is True
    assert "process_failed" in result["stop_reason"]


def test_apply_retry_policy_empty_output_same_as_process_failed():
    r1 = _apply_retry_policy("T001", "empty_output", {})
    r2 = _apply_retry_policy("T001", "process_failed", {})
    assert r1["retry_count"] == r2["retry_count"]


# ── _is_blocked_by_retry ──────────────────────────────────────────────────────

def test_is_blocked_by_retry_empty_state_not_blocked():
    assert _is_blocked_by_retry("T001", {}) is False


def test_is_blocked_by_retry_stopped_returns_true():
    assert _is_blocked_by_retry("T001", {"stopped": True, "stop_reason": "unknown"}) is True


def test_is_blocked_by_retry_cooldown_in_future_returns_true():
    state = {"cooldown_until": _future_iso(3600)}
    assert _is_blocked_by_retry("T001", state) is True


def test_is_blocked_by_retry_cooldown_in_past_not_blocked():
    state = {"cooldown_until": _past_iso(3600)}
    assert _is_blocked_by_retry("T001", state) is False


def test_is_blocked_by_retry_logs_remaining_seconds_when_in_cooldown(capsys):
    state = {"cooldown_until": _future_iso(3600)}
    _is_blocked_by_retry("T001", state)
    out = capsys.readouterr().out
    assert "cooldown" in out
    assert "T001" in out


def test_is_blocked_by_retry_logs_human_attention_when_stopped(capsys):
    state = {"stopped": True, "stop_reason": "write_permission_missing"}
    _is_blocked_by_retry("T001", state)
    out = capsys.readouterr().out
    assert "human attention" in out


# ── run_once skips blocked tickets ───────────────────────────────────────────

def test_run_once_skips_ticket_in_cooldown(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    _save_retry_state(run_dir, {"cooldown_until": _future_iso(3600)})
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_not_called()


def test_run_once_skips_stopped_ticket(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    _save_retry_state(run_dir, {"stopped": True, "stop_reason": "write_permission_missing"})
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_not_called()


def test_run_once_launches_ticket_with_elapsed_cooldown(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    _save_retry_state(run_dir, {"cooldown_until": _past_iso(3600)})
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_called_once()


def test_run_once_launches_ticket_with_no_retry_state(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs)
    mock_launch.assert_called_once()


# ── launch_ticket retry state integration ────────────────────────────────────

def _make_mock_result(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    m.pid = 4242
    m.poll.return_value = None
    return m


def _launch_preflight_ok(*, branch: str = "ticket/T001"):
    return patch.multiple(
        "run_daemon",
        _sync_ticket_branch=MagicMock(return_value=True),
        _ensure_clean_working_tree=MagicMock(return_value=True),
        _get_current_branch=MagicMock(return_value=branch),
    )


def test_launch_ticket_reclassifies_claude_quota_from_output(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: process_failed (rc=1)\n",
        encoding="utf-8",
    )
    (run_dir / "tester-output.md").write_text(
        "You've hit your limit · resets 9:40pm (Europe/Paris)\n",
        encoding="utf-8",
    )
    proc = _make_mock_result(1)
    proc.poll.return_value = 1
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    reap_completed_workers(runs)
    state = _load_retry_state(run_dir)
    assert state.get("failure_class") == "quota_exceeded"
    assert state.get("quota_message")
    assert "cooldown_until" in state


def test_launch_ticket_saves_retry_state_on_failure(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: quota_exceeded (rc=1)\n",
        encoding="utf-8",
    )
    proc = _make_mock_result(1)
    proc.poll.return_value = 1
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    reap_completed_workers(runs)
    state = _load_retry_state(run_dir)
    assert state.get("failure_class") == "quota_exceeded"
    assert "cooldown_until" in state


def test_launch_ticket_clears_retry_state_on_success(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    _save_retry_state(run_dir, {"failure_class": "quota_exceeded", "retry_count": 1})
    proc = _make_mock_result(0)
    proc.poll.return_value = 0
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    reap_completed_workers(runs)
    assert not _retry_state_path(run_dir).exists()


def test_launch_ticket_no_retry_state_when_no_failure_class_in_log(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run start: state=PLAN_APPROVED\n",
        encoding="utf-8",
    )
    proc = _make_mock_result(1)
    proc.poll.return_value = 1
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    reap_completed_workers(runs)
    assert not _retry_state_path(run_dir).exists()


def test_launch_ticket_stops_on_write_permission_missing(tmp_path):
    import run_daemon

    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text(
        "[2026-01-01T00:00:00Z] auto-run: runtime failure: write_permission_missing (rc=0)\n",
        encoding="utf-8",
    )
    proc = _make_mock_result(1)
    proc.poll.return_value = 1
    run_daemon._ACTIVE_WORKERS.clear()
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=proc):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    reap_completed_workers(runs)
    state = _load_retry_state(run_dir)
    assert state.get("stopped") is True


def test_launch_ticket_dry_run_does_not_save_retry_state(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _write_state(runs, "T001", "PLAN_APPROVED")
    launch_ticket("T001", "test-cmd", dry_run=True, runs_dir=runs)
    assert not _retry_state_path(run_dir).exists()
