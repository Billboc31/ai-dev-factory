"""Unit tests for project isolation in daemon_manager, artifact_reader, and runtime_resolver.

Verifies that service functions never read from a project root other than the one
passed in, using two separate temporary directories.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services import artifact_reader, daemon_manager
from services.control_api.services.runtime_resolver import (
    resolve_logs_dir,
    resolve_runs_dir,
    resolve_state_dir,
    resolve_worktrees_dir,
)


# ── runtime_resolver: separate dirs per project root ─────────────────────────

def test_resolve_runs_dir_separate_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    assert resolve_runs_dir(root_a) != resolve_runs_dir(root_b)
    assert resolve_runs_dir(root_a) == root_a / "runs"
    assert resolve_runs_dir(root_b) == root_b / "runs"


def test_resolve_logs_dir_separate_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    assert resolve_logs_dir(root_a) != resolve_logs_dir(root_b)


def test_resolve_worktrees_dir_separate_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    assert resolve_worktrees_dir(root_a) != resolve_worktrees_dir(root_b)


# ── daemon_manager: reads only from the given project_root ────────────────────

def test_daemon_status_reads_only_given_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    for r in (root_a, root_b):
        (r / "runs").mkdir(parents=True)

    pid = os.getpid()
    (root_a / "runs" / "daemon.pid").write_text(
        json.dumps({"pid": pid, "started_at": "2026-01-01T00:00:00Z"})
    )

    status_a = daemon_manager.get_status(root_a)
    status_b = daemon_manager.get_status(root_b)

    assert status_a.running is True
    assert status_b.running is False


def test_daemon_activity_reads_only_given_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    for r in (root_a, root_b):
        (r / "runs").mkdir(parents=True)
    (root_a / "logs").mkdir(parents=True)
    (root_a / "logs" / "daemon.log").write_text("project-a log line\n")

    lines_a = daemon_manager.get_activity(root_a)
    lines_b = daemon_manager.get_activity(root_b)

    assert any("project-a log line" in l for l in lines_a)
    assert not any("project-a log line" in l for l in lines_b)


def test_runtime_status_reads_only_given_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"

    run_dir_a = root_a / "runs" / "T001"
    run_dir_a.mkdir(parents=True)
    (run_dir_a / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"})
    )
    (root_b / "runs").mkdir(parents=True)

    status_a = daemon_manager.get_runtime_status(root_a)
    status_b = daemon_manager.get_runtime_status(root_b)

    assert any(e.title == "T001" for e in status_a.intake_queue)
    assert not any(e.title == "T001" for e in status_b.intake_queue)


# ── artifact_reader: reads only from the given project_root ───────────────────

def test_list_tickets_reads_only_given_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"

    run_dir = root_a / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"})
    )
    (root_b / "runs").mkdir(parents=True)

    tickets_a = artifact_reader.list_tickets(root_a)
    tickets_b = artifact_reader.list_tickets(root_b)

    assert any(t.ticket_id == "T001" for t in tickets_a)
    assert not any(t.ticket_id == "T001" for t in tickets_b)


def test_get_ticket_returns_none_for_wrong_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"

    run_dir = root_a / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"})
    )
    (root_b / "runs").mkdir(parents=True)

    ticket_from_b = artifact_reader.get_ticket(root_b, "T001")
    assert ticket_from_b is None


def test_ticket_logs_isolated_per_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"

    run_dir_a = root_a / "runs" / "T001"
    run_dir_a.mkdir(parents=True)
    (run_dir_a / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "PLAN_APPROVED", "branch": "ticket/T001-work"})
    )
    (run_dir_a / "runtime.log").write_text("project-a specific log\n")
    (root_b / "runs").mkdir(parents=True)

    logs_a = artifact_reader.get_ticket_logs(root_a, "T001")
    assert logs_a is not None
    assert "project-a specific log" in logs_a

    logs_b = artifact_reader.get_ticket_logs(root_b, "T001")
    assert logs_b is None
