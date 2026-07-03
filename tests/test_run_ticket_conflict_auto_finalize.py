"""Tests for auto-finalize after conflict resolution (project rule)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ticket_dir = tmp_path / "runs" / "T001"
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "state.json").write_text(
        json.dumps({
            "ticket_id": "T001",
            "state": "CONFLICT_RESOLVED_REVIEW_NEEDED",
            "pre_conflict_state": "TEST_COMPLETE",
            "branch": "ticket/T001-x",
            "project_id": "proj-a",
        })
    )
    return tmp_path


def _import_run_ticket():
    import importlib
    return importlib.import_module("run_ticket")


def test_auto_finalize_skipped_when_gate_enabled(workdir, monkeypatch):
    rt = _import_run_ticket()

    class _Engine:
        @staticmethod
        def is_human_conflict_resolution_approval_required(_db_path, _pid):
            return True

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            return workdir / "fake.sqlite"

    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)

    state = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert rt._maybe_auto_finalize_conflict_resolution("T001", state) is None
    saved = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert saved["state"] == "CONFLICT_RESOLVED_REVIEW_NEEDED"


def test_auto_finalize_transitions_and_runs_pr_lifecycle(workdir, monkeypatch):
    rt = _import_run_ticket()
    calls = {"pr": 0}

    class _Engine:
        @staticmethod
        def is_human_conflict_resolution_approval_required(_db_path, _pid):
            return False

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            return workdir / "fake.sqlite"

    def _fake_finalize(ticket_id):
        calls["pr"] += 1
        assert ticket_id == "T001"

    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)
    monkeypatch.setattr(rt, "_finalize_test_complete_pr", _fake_finalize)

    state = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    result = rt._maybe_auto_finalize_conflict_resolution("T001", state)
    assert result == "TEST_COMPLETE"
    assert calls["pr"] == 1
    saved = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert saved["state"] == "TEST_COMPLETE"
