"""Tests for automatic ticket intelligence/readiness pipeline."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_pipeline",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()

import ticket_pipeline as pipeline  # noqa: E402


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "pipeline.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_AUTO_TICKET_PIPELINE", raising=False)


def test_auto_pipeline_enabled_by_default(db, env):
    assert pipeline.is_auto_pipeline_enabled(db) is True


def test_auto_pipeline_respects_env_off(db, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_AUTO_TICKET_PIPELINE", "off")
    assert pipeline.is_auto_pipeline_enabled(db) is False


def test_find_next_ticket_prefers_missing_intelligence(db):
    _db.upsert_ticket_runtime(db, "T002", state="INIT")
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="completed")
    _db.upsert_ticket_readiness(db, "T001", readiness_status="ready_candidate")

    assert pipeline.find_next_ticket(db, ["T001", "T002"]) == "T002"


def test_find_next_ticket_picks_readiness_when_intel_done(db):
    _db.upsert_ticket_runtime(db, "T003", state="INIT")
    _db.upsert_ticket_intelligence(db, "T003", analysis_status="completed")

    assert pipeline.find_next_ticket(db, ["T003"]) == "T003"


def test_process_ticket_runs_intelligence_then_readiness(db, tmp_path, monkeypatch):
    project_root = tmp_path / "repo"
    run_dir = project_root / "runs" / "T010"
    run_dir.mkdir(parents=True)
    (run_dir / "ticket.md").write_text("# T010\n\nno deps\n", encoding="utf-8")

    intel_calls: list[str] = []
    ready_calls: list[str] = []

    def _fake_intel(db_path, ticket_id, content, exec_cmd, root, project_id=None):
        intel_calls.append(ticket_id)
        _db.upsert_ticket_intelligence(db_path, ticket_id, analysis_status="completed")

    def _fake_ready(db_path, ticket_id, content, root, **kwargs):
        ready_calls.append(ticket_id)
        _db.upsert_ticket_readiness(db_path, ticket_id, readiness_status="ready_candidate")

    monkeypatch.setattr("ticket_intelligence_analyzer.run_analysis", _fake_intel)
    monkeypatch.setattr(pipeline, "run_evaluation", _fake_ready)

    ran = pipeline.process_ticket(
        db, "T010", project_root, "claude --print", project_id="proj-a",
    )
    assert ran is True
    assert intel_calls == ["T010"]
    assert ready_calls == []


def test_process_ticket_runs_readiness_when_intel_already_completed(db, tmp_path, monkeypatch):
    project_root = tmp_path / "repo"
    run_dir = project_root / "runs" / "T011"
    run_dir.mkdir(parents=True)
    (run_dir / "ticket.md").write_text("# T011\n\nno deps\n", encoding="utf-8")
    _db.upsert_ticket_intelligence(db, "T011", analysis_status="completed")

    ready_calls: list[str] = []

    def _fake_intel(*args, **kwargs):
        raise AssertionError("intelligence should not run")

    def _fake_ready(db_path, ticket_id, content, root, **kwargs):
        ready_calls.append(ticket_id)
        _db.upsert_ticket_readiness(db_path, ticket_id, readiness_status="blocked")

    monkeypatch.setattr("ticket_intelligence_analyzer.run_analysis", _fake_intel)
    monkeypatch.setattr(pipeline, "run_evaluation", _fake_ready)

    ran = pipeline.process_ticket(
        db, "T011", project_root, "claude --print", project_id="proj-a",
    )
    assert ran is True
    assert ready_calls == ["T011"]


def test_maybe_run_readiness_after_intelligence(db, tmp_path, monkeypatch):
    project_root = tmp_path / "repo"
    ready_calls: list[str] = []

    def _fake_ready(db_path, ticket_id, content, root, **kwargs):
        ready_calls.append(ticket_id)
        _db.upsert_ticket_readiness(db_path, ticket_id, readiness_status="ready_candidate")

    monkeypatch.setattr(pipeline, "run_evaluation", _fake_ready)

    pipeline.maybe_run_readiness_after_intelligence(
        db, "T012", "# T012\n", project_root,
    )
    assert ready_calls == ["T012"]
