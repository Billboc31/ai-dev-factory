"""Tests for T018 — runtime capability and failure detection."""

import json
import datetime
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import classify_runtime_failure, extract_quota_alert_info, parse_quota_reset_at


# ── classify_runtime_failure — category coverage ─────────────────────────────

def test_process_crashed():
    assert classify_runtime_failure(-9, "", "") == "process_crashed"


def test_process_crashed_any_negative_rc():
    assert classify_runtime_failure(-1, "some output", "some error") == "process_crashed"


def test_quota_exceeded_in_stderr():
    assert classify_runtime_failure(1, "", "rate limit exceeded") == "quota_exceeded"


def test_quota_exceeded_in_stdout():
    assert classify_runtime_failure(1, "too many requests", "") == "quota_exceeded"


def test_quota_exceeded_rc_zero():
    assert classify_runtime_failure(0, "ratelimiterror occurred", "") == "quota_exceeded"


def test_write_permission_missing_rc_zero():
    assert classify_runtime_failure(0, "I need write permission\nPlease grant it", "") == "write_permission_missing"


def test_write_permission_missing_nonzero_rc():
    assert classify_runtime_failure(1, "write permission required", "") == "write_permission_missing"


def test_provider_error_in_stderr():
    assert classify_runtime_failure(1, "", "internal server error") == "provider_error"


def test_provider_error_overloaded():
    assert classify_runtime_failure(1, "overloaded_error", "") == "provider_error"


def test_empty_output_rc_zero():
    assert classify_runtime_failure(0, "", "") == "empty_output"


def test_empty_output_whitespace_only():
    assert classify_runtime_failure(0, "   \n  \t", "") == "empty_output"


def test_process_failed():
    assert classify_runtime_failure(1, "some non-empty output", "") == "process_failed"


def test_unknown():
    assert classify_runtime_failure(0, "normal step output here", "") == "unknown"


def test_quota_exceeded_claude_hit_limit():
    msg = "You've hit your limit · resets 9:40pm (Europe/Paris)"
    assert classify_runtime_failure(1, msg, "") == "quota_exceeded"


def test_extract_quota_alert_info_claude_message():
    msg = "You've hit your limit · resets 9:40pm (Europe/Paris)"
    info = extract_quota_alert_info(msg)
    assert info is not None
    assert "hit your limit" in info["message"].lower()
    assert info.get("reset_at", "").endswith("Z")


def test_parse_quota_reset_at_returns_future_utc():
    with patch("run_step.datetime") as mock_dt:
        from zoneinfo import ZoneInfo

        paris = ZoneInfo("Europe/Paris")
        mock_dt.datetime.now.return_value = datetime.datetime(2026, 6, 26, 18, 0, tzinfo=paris)
        mock_dt.timedelta = datetime.timedelta
        mock_dt.timezone = datetime.timezone
        reset = parse_quota_reset_at("resets 9:40pm (Europe/Paris)")
    assert reset is not None
    assert reset.endswith("Z")


# ── priority ordering ─────────────────────────────────────────────────────────

def test_priority_quota_over_write_permission():
    combined = "rate limit exceeded — write permission missing"
    assert classify_runtime_failure(1, combined, "") == "quota_exceeded"


def test_priority_quota_over_provider_error():
    combined = "quota exceeded — internal server error"
    assert classify_runtime_failure(1, combined, "") == "quota_exceeded"


def test_priority_write_permission_over_empty_output():
    assert classify_runtime_failure(0, "please grant write permission", "") == "write_permission_missing"


# ── state unchanged invariant ─────────────────────────────────────────────────

def test_state_unchanged_on_step_failure(tmp_path, monkeypatch):
    """auto_run must leave state unchanged when the step process fails."""
    run_dir = tmp_path / "runs" / "T999"
    run_dir.mkdir(parents=True)
    state = {
        "ticket_id": "T999",
        "state": "PLAN_APPROVED",
        "branch": "ticket/T999-work",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (run_dir / "state.json").write_text(json.dumps(state))

    monkeypatch.chdir(tmp_path)

    import run_ticket

    monkeypatch.setattr(run_ticket, "_get_current_branch", lambda: "ticket/T999-work")
    monkeypatch.setattr(run_ticket, "_check_working_tree_clean", lambda: None)
    monkeypatch.setattr(
        run_ticket,
        "_call_run_step",
        lambda *a, **kw: (1, "", tmp_path / "fake-output.md"),
    )

    rc = run_ticket.auto_run("T999", "echo test")
    assert rc == 2

    saved = json.loads((run_dir / "state.json").read_text())
    assert saved["state"] == "PLAN_APPROVED"


# ── runtime log contains diagnostic ──────────────────────────────────────────

def test_runtime_log_contains_failure_class(tmp_path, monkeypatch):
    """auto_run must log the failure class when a step fails."""
    run_dir = tmp_path / "runs" / "T999"
    run_dir.mkdir(parents=True)
    state = {
        "ticket_id": "T999",
        "state": "PLAN_APPROVED",
        "branch": "ticket/T999-work",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (run_dir / "state.json").write_text(json.dumps(state))

    monkeypatch.chdir(tmp_path)

    import run_ticket

    monkeypatch.setattr(run_ticket, "_get_current_branch", lambda: "ticket/T999-work")
    monkeypatch.setattr(run_ticket, "_check_working_tree_clean", lambda: None)
    monkeypatch.setattr(
        run_ticket,
        "_call_run_step",
        lambda *a, **kw: (1, "rate limit exceeded", tmp_path / "fake-output.md"),
    )

    run_ticket.auto_run("T999", "echo test")

    log = (run_dir / "runtime.log").read_text()
    assert "quota_exceeded" in log
