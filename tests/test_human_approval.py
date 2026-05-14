"""Tests for T021 — human approval commands."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import (
    HUMAN_APPROVAL_TRANSITIONS,
    apply_human_approval,
    main,
)


def _write_state(run_dir: Path, state: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "ticket_id": "T999",
        "state": state,
        "branch": "ticket/T999-work",
        "updated_at": "2026-01-01T00:00:00Z",
    }))


def _read_state(run_dir: Path) -> str:
    return json.loads((run_dir / "state.json").read_text())["state"]


# ── HUMAN_APPROVAL_TRANSITIONS table ─────────────────────────────────────────

def test_transitions_table_has_four_entries():
    assert len(HUMAN_APPROVAL_TRANSITIONS) == 4


def test_transitions_table_keys():
    assert set(HUMAN_APPROVAL_TRANSITIONS) == {
        "approve-plan",
        "request-plan-fix",
        "approve-implementation",
        "request-implementation-fix",
    }


# ── Valid transitions ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("command,initial,expected", [
    ("approve-plan",               "PLAN_REVIEW_NEEDED",           "PLAN_APPROVED"),
    ("request-plan-fix",           "PLAN_REVIEW_NEEDED",           "PLAN_FIX_REQUIRED"),
    ("approve-implementation",     "IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_APPROVED"),
    ("request-implementation-fix", "IMPLEMENTATION_REVIEW_NEEDED", "IMPLEMENTATION_FIX_REQUIRED"),
])
def test_valid_transition(command, initial, expected):
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, initial)
            rc = apply_human_approval("T999", command)
            assert rc == 0
            assert _read_state(run_dir) == expected
        finally:
            os.chdir(orig)


# ── Invalid transitions (wrong current state) ─────────────────────────────────

def test_approve_plan_refused_when_not_in_review(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, "PLAN_APPROVED")
            rc = apply_human_approval("T999", "approve-plan")
            assert rc == 2
            assert _read_state(run_dir) == "PLAN_APPROVED"  # unchanged
            captured = capsys.readouterr()
            assert "PLAN_REVIEW_NEEDED" in captured.err
        finally:
            os.chdir(orig)


def test_approve_implementation_refused_when_not_in_review(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, "PLAN_APPROVED")
            rc = apply_human_approval("T999", "approve-implementation")
            assert rc == 2
            assert _read_state(run_dir) == "PLAN_APPROVED"
            captured = capsys.readouterr()
            assert "IMPLEMENTATION_REVIEW_NEEDED" in captured.err
        finally:
            os.chdir(orig)


# ── runtime.log is written ────────────────────────────────────────────────────

def test_approval_is_logged():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, "PLAN_REVIEW_NEEDED")
            apply_human_approval("T999", "approve-plan")
            log = (run_dir / "runtime.log").read_text()
            assert "human-approval" in log
            assert "approve-plan" in log
            assert "PLAN_APPROVED" in log
        finally:
            os.chdir(orig)


# ── CLI wiring ────────────────────────────────────────────────────────────────

def test_cli_approve_plan():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, "PLAN_REVIEW_NEEDED")
            rc = main(["T999", "--approve-plan"])
            assert rc == 0
            assert _read_state(run_dir) == "PLAN_APPROVED"
        finally:
            os.chdir(orig)


def test_set_state_still_works():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            run_dir = Path(tmp) / "runs" / "T999"
            _write_state(run_dir, "INIT")
            rc = main(["T999", "--set-state", "PLAN_REVIEW_NEEDED"])
            assert rc == 0
            assert _read_state(run_dir) == "PLAN_REVIEW_NEEDED"
        finally:
            os.chdir(orig)
