"""Tests for GET /tickets/{ticket_id}/timeline endpoint."""

from __future__ import annotations

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path)


def _make_ticket(tmp_path: Path, ticket_id: str, state: str, **extra) -> Path:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    data = {"ticket_id": ticket_id, "state": state, **extra}
    (run_dir / "state.json").write_text(json.dumps(data), encoding="utf-8")
    return run_dir


def _step(steps: list, step_id: str) -> dict:
    return next((s for s in steps if s["id"] == step_id), None)


# ── 404 ───────────────────────────────────────────────────────────────────────

def test_timeline_404(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T999/timeline")
    assert r.status_code == 404


# ── INIT ──────────────────────────────────────────────────────────────────────

def test_timeline_init(tmp_path):
    _make_ticket(tmp_path, "T001", "INIT")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["current_state"] == "INIT"
    assert body["human_gate"] is False
    assert body["current_agent"] == "planner"
    assert _step(body["steps"], "issue_intake")["status"] == "done"
    assert _step(body["steps"], "plan")["status"] == "running"
    assert _step(body["steps"], "plan")["agent"] == "planner"
    assert _step(body["steps"], "implementation")["status"] == "pending"


# ── PLAN_REVIEW_NEEDED ────────────────────────────────────────────────────────

def test_timeline_plan_review_needed(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_REVIEW_NEEDED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["human_gate"] is True
    assert body["current_agent"] is None
    assert _step(body["steps"], "plan")["status"] == "done"
    assert _step(body["steps"], "plan_review")["status"] == "waiting_human"
    assert _step(body["steps"], "implementation")["status"] == "pending"


# ── PLAN_APPROVED ─────────────────────────────────────────────────────────────

def test_timeline_plan_approved(tmp_path):
    _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["human_gate"] is False
    assert body["current_agent"] == "coder"
    assert _step(body["steps"], "plan_review")["status"] == "done"
    assert _step(body["steps"], "implementation")["status"] == "running"
    assert _step(body["steps"], "implementation")["agent"] == "coder"
    assert _step(body["steps"], "implementation_review")["status"] == "pending"


# ── IMPLEMENTATION_REVIEW_NEEDED ──────────────────────────────────────────────

def test_timeline_implementation_review_needed(tmp_path):
    _make_ticket(tmp_path, "T001", "IMPLEMENTATION_REVIEW_NEEDED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["human_gate"] is True
    assert body["current_agent"] is None
    assert _step(body["steps"], "implementation")["status"] == "done"
    assert _step(body["steps"], "implementation_review")["status"] == "waiting_human"
    assert _step(body["steps"], "fix_loop")["status"] == "pending"


# ── IMPLEMENTATION_FIX_REQUIRED ───────────────────────────────────────────────

def test_timeline_implementation_fix_required(tmp_path):
    _make_ticket(tmp_path, "T001", "IMPLEMENTATION_FIX_REQUIRED")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["human_gate"] is False
    assert body["current_agent"] == "coder"
    assert _step(body["steps"], "implementation_review")["status"] == "done"
    assert _step(body["steps"], "fix_loop")["status"] == "running"
    assert _step(body["steps"], "fix_loop")["agent"] == "coder"
    assert _step(body["steps"], "tests")["status"] == "pending"


# ── TEST_COMPLETE ─────────────────────────────────────────────────────────────

def test_timeline_test_complete_no_retry(tmp_path):
    _make_ticket(tmp_path, "T001", "TEST_COMPLETE")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["current_agent"] is None
    assert body["human_gate"] is False
    assert _step(body["steps"], "tests")["status"] == "done"
    assert _step(body["steps"], "fix_loop")["status"] == "skipped"


def test_timeline_test_complete_with_retry(tmp_path):
    run_dir = _make_ticket(tmp_path, "T001", "TEST_COMPLETE")
    (run_dir / "retry-state.json").write_text(json.dumps({"retries": 1}), encoding="utf-8")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    body = r.json()
    assert _step(body["steps"], "fix_loop")["status"] == "done"
    assert _step(body["steps"], "tests")["status"] == "done"


# ── last_event from runtime.log ───────────────────────────────────────────────

def test_timeline_last_event(tmp_path):
    run_dir = _make_ticket(tmp_path, "T001", "PLAN_APPROVED")
    (run_dir / "runtime.log").write_text("first line\nlast line\n", encoding="utf-8")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/timeline")
    assert r.status_code == 200
    assert r.json()["last_event"] == "last line"
