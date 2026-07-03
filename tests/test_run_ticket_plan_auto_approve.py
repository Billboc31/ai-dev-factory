"""Tests for the plan auto-approval branch of run_ticket.

Covers ``_maybe_auto_approve_plan``: the helper that consults
``execution_rules_engine.is_human_plan_approval_required`` after the planner
step and, when the gate is disabled for the project, writes a `plan` approval
row via ``ticket_approval_service.auto_approve_plan``, updates ``state.json``
to ``PLAN_APPROVED``, and appends a workflow journal entry.
"""

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
            "state": "PLAN_REVIEW_NEEDED",
            "branch": "ticket/T001-x",
        })
    )
    return tmp_path


def _import_run_ticket():
    # Import the module in-place; avoid a fresh reload so other test files that
    # bind names off ``run_ticket`` at collection time keep observing the same
    # object (patching ``run_ticket.run_command`` in a sibling test must still
    # affect the function they hold a reference to).
    import importlib
    return importlib.import_module("run_ticket")


def test_auto_approve_skipped_when_gate_enabled(workdir, monkeypatch):
    rt = _import_run_ticket()

    calls = {"gate_lookup": 0, "auto_approve": 0}

    class _Engine:
        @staticmethod
        def is_human_plan_approval_required(_db_path, _pid):
            calls["gate_lookup"] += 1
            return True

    class _Service:
        @staticmethod
        def auto_approve_plan(*_a, **_kw):
            calls["auto_approve"] += 1
            raise AssertionError("auto_approve_plan must not be called when gate is enabled")

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            return workdir / ".runtime" / "fake.sqlite"

    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "ticket_approval_service", _Service)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)

    state = {
        "ticket_id": "T001",
        "state": "PLAN_REVIEW_NEEDED",
        "branch": "ticket/T001-x",
        "project_id": "proj-a",
    }
    result = rt._maybe_auto_approve_plan("T001", state)
    assert result is None
    assert calls["gate_lookup"] == 1
    assert calls["auto_approve"] == 0

    # state.json unchanged
    persisted = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert persisted["state"] == "PLAN_REVIEW_NEEDED"


def test_auto_approve_fires_when_gate_disabled(workdir, monkeypatch):
    rt = _import_run_ticket()

    inserted_rows = []

    class _Engine:
        @staticmethod
        def is_human_plan_approval_required(_db_path, _pid):
            return False

    class _Service:
        @staticmethod
        def auto_approve_plan(_db_path, ticket_id, *, reason="PROJECT_SETTING"):
            inserted_rows.append({
                "ticket_id": ticket_id,
                "approval_type": "plan",
                "approval_status": "approved",
                "approved_by": "SYSTEM",
                "approval_comment": reason,
            })
            return inserted_rows[-1]

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            return workdir / ".runtime" / "fake.sqlite"

    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "ticket_approval_service", _Service)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)

    state = {
        "ticket_id": "T001",
        "state": "PLAN_REVIEW_NEEDED",
        "branch": "ticket/T001-x",
        "project_id": "proj-a",
    }
    result = rt._maybe_auto_approve_plan("T001", state)
    assert result == "PLAN_APPROVED"
    assert len(inserted_rows) == 1
    assert inserted_rows[0]["approval_comment"] == "PROJECT_SETTING"

    persisted = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert persisted["state"] == "PLAN_APPROVED"

    journal = (workdir / "runs" / "T001" / "workflow-status.md").read_text()
    assert "auto-approve" in journal
    assert "PLAN_REVIEW_NEEDED" in journal
    assert "PLAN_APPROVED" in journal

    log = (workdir / "runs" / "T001" / "runtime.log").read_text()
    assert "plan approval gate disabled" in log
    assert "PROJECT_SETTING" in log


def test_auto_approve_falls_back_to_env_project_name(workdir, monkeypatch):
    rt = _import_run_ticket()

    seen_project = {}

    class _Engine:
        @staticmethod
        def is_human_plan_approval_required(_db_path, pid):
            seen_project["pid"] = pid
            return False

    class _Service:
        @staticmethod
        def auto_approve_plan(*_a, **_kw):
            return {"id": 1}

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            seen_project["db_pid"] = project_id
            return workdir / ".runtime" / "fake.sqlite"

    monkeypatch.setenv("PROJECT_NAME", "env-project")
    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "ticket_approval_service", _Service)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)

    state = {"ticket_id": "T001", "state": "PLAN_REVIEW_NEEDED"}
    rt._maybe_auto_approve_plan("T001", state)
    assert seen_project["pid"] == "env-project"
    assert seen_project["db_pid"] == "env-project"


def test_auto_approve_no_op_when_db_path_missing(workdir, monkeypatch):
    rt = _import_run_ticket()

    class _Engine:
        @staticmethod
        def is_human_plan_approval_required(*_a, **_kw):
            raise AssertionError("should not be called when db_path is None")

    class _Service:
        @staticmethod
        def auto_approve_plan(*_a, **_kw):
            raise AssertionError("should not be called when db_path is None")

    class _DB:
        @staticmethod
        def get_db_path(project_id=None):
            return None

    monkeypatch.setitem(sys.modules, "execution_rules_engine", _Engine)
    monkeypatch.setitem(sys.modules, "ticket_approval_service", _Service)
    monkeypatch.setitem(sys.modules, "runtime_db", _DB)

    state = {"ticket_id": "T001", "state": "PLAN_REVIEW_NEEDED", "project_id": "proj-a"}
    assert rt._maybe_auto_approve_plan("T001", state) is None

    persisted = json.loads((workdir / "runs" / "T001" / "state.json").read_text())
    assert persisted["state"] == "PLAN_REVIEW_NEEDED"
