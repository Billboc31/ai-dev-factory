"""Tests for artifact_reader — read-only access, ticket listing, artifact paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services import artifact_reader


def _make_ticket(runs_root: Path, ticket_id: str, state: str, **extra) -> Path:
    run_dir = runs_root / ticket_id
    run_dir.mkdir(parents=True)
    data = {"ticket_id": ticket_id, "state": state, **extra}
    (run_dir / "state.json").write_text(json.dumps(data), encoding="utf-8")
    return run_dir


# ── validate_ticket_id ────────────────────────────────────────────────────────

def test_validate_ok():
    artifact_reader.validate_ticket_id("T001")
    artifact_reader.validate_ticket_id("T1234")


def test_validate_bad():
    with pytest.raises(ValueError):
        artifact_reader.validate_ticket_id("INVALID")
    with pytest.raises(ValueError):
        artifact_reader.validate_ticket_id("T1")
    with pytest.raises(ValueError):
        artifact_reader.validate_ticket_id("")


# ── list_tickets ──────────────────────────────────────────────────────────────

def test_list_tickets_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    assert artifact_reader.list_tickets(tmp_path) == []


def test_list_tickets_ignores_non_ticket_dirs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "daemon.pid").write_text("{}")
    (runs / "notadir").write_text("x")
    assert artifact_reader.list_tickets(tmp_path) == []


def test_list_tickets_returns_all(tmp_path):
    runs = tmp_path / "runs"
    _make_ticket(runs, "T001", "PLAN_APPROVED")
    _make_ticket(runs, "T002", "TEST_COMPLETE")
    result = artifact_reader.list_tickets(tmp_path)
    ids = {t.ticket_id for t in result}
    assert ids == {"T001", "T002"}


def test_list_tickets_skips_corrupted_state(tmp_path):
    runs = tmp_path / "runs"
    run_dir = runs / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("NOT JSON")
    result = artifact_reader.list_tickets(tmp_path)
    assert result == []


# ── get_ticket ────────────────────────────────────────────────────────────────

def test_get_ticket_ok(tmp_path):
    runs = tmp_path / "runs"
    _make_ticket(runs, "T001", "PLAN_APPROVED", branch="ticket/T001-work")
    t = artifact_reader.get_ticket(tmp_path, "T001")
    assert t is not None
    assert t.ticket_id == "T001"
    assert t.state == "PLAN_APPROVED"
    assert t.branch == "ticket/T001-work"


def test_get_ticket_not_found(tmp_path):
    (tmp_path / "runs").mkdir()
    assert artifact_reader.get_ticket(tmp_path, "T999") is None


def test_get_ticket_invalid_id(tmp_path):
    with pytest.raises(ValueError):
        artifact_reader.get_ticket(tmp_path, "bad")


# ── get_ticket_logs ───────────────────────────────────────────────────────────

def test_get_logs_ok(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text("line1\nline2\n")
    logs = artifact_reader.get_ticket_logs(tmp_path, "T001")
    assert logs == "line1\nline2\n"


def test_get_logs_missing(tmp_path):
    runs = tmp_path / "runs"
    _make_ticket(runs, "T001", "PLAN_APPROVED")
    assert artifact_reader.get_ticket_logs(tmp_path, "T001") is None


# ── get_ticket_artifacts ──────────────────────────────────────────────────────

def test_get_artifacts_lists_files(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "PLAN_APPROVED")
    (run_dir / "plan.md").write_text("plan")
    reviews = run_dir / "reviews"
    reviews.mkdir()
    (reviews / "review.md").write_text("review")
    artifacts = artifact_reader.get_ticket_artifacts(tmp_path, "T001")
    assert "plan.md" in artifacts
    assert "reviews/review.md" in artifacts


def test_get_artifacts_empty_dir(tmp_path):
    runs = tmp_path / "runs"
    _make_ticket(runs, "T001", "PLAN_APPROVED")
    artifacts = artifact_reader.get_ticket_artifacts(tmp_path, "T001")
    assert "state.json" in artifacts


# ── get_ticket_plan / review / tests ─────────────────────────────────────────

def test_get_plan_ok(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "PLAN_APPROVED")
    (run_dir / "plan.md").write_text("# Plan content")
    assert artifact_reader.get_ticket_plan(tmp_path, "T001") == "# Plan content"


def test_get_plan_missing(tmp_path):
    runs = tmp_path / "runs"
    _make_ticket(runs, "T001", "PLAN_APPROVED")
    assert artifact_reader.get_ticket_plan(tmp_path, "T001") is None


def test_get_review_ok(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "IMPLEMENTATION_REVIEW_NEEDED")
    reviews = run_dir / "reviews"
    reviews.mkdir()
    (reviews / "review.md").write_text("APPROVED")
    assert artifact_reader.get_ticket_review(tmp_path, "T001") == "APPROVED"


def test_get_tests_ok(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "TEST_COMPLETE")
    tests = run_dir / "tests"
    tests.mkdir()
    (tests / "test-report.md").write_text("All pass")
    assert artifact_reader.get_ticket_tests(tmp_path, "T001") == "All pass"


# ── never writes to state.json ────────────────────────────────────────────────

def test_artifact_reader_does_not_write(tmp_path):
    runs = tmp_path / "runs"
    run_dir = _make_ticket(runs, "T001", "PLAN_APPROVED")
    state_path = run_dir / "state.json"
    mtime_before = state_path.stat().st_mtime

    artifact_reader.get_ticket(tmp_path, "T001")
    artifact_reader.list_tickets(tmp_path)
    artifact_reader.get_ticket_logs(tmp_path, "T001")
    artifact_reader.get_ticket_artifacts(tmp_path, "T001")
    artifact_reader.get_ticket_plan(tmp_path, "T001")

    mtime_after = state_path.stat().st_mtime
    assert mtime_before == mtime_after, "artifact_reader must not write state.json"
