"""Tests for ticket_intelligence_analyzer subprocess failure handling (T206, T208)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_analyzer_test_runtime_db_sqlite",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    saved = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if saved is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = saved
    return mod


def _load_analyzer_against(sqlite_db_mod):
    spec = importlib.util.spec_from_file_location(
        "_analyzer_test_module",
        _TOOLS / "ticket_intelligence_analyzer.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.runtime_db = sqlite_db_mod
    return mod


_db = _load_sqlite_runtime_db()
_analyzer = _load_analyzer_against(_db)


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


# Minimal stand-in for ``subprocess.Popen``. The analyzer drives it via
# ``Popen(...).communicate(input=..., timeout=...)`` then reads ``returncode``,
# so the fake only has to honour that small contract.
class _FakePopen:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        raise_timeout: bool = False,
        record_kill: list | None = None,
    ) -> None:
        self._returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._raise_timeout = raise_timeout
        self._communicate_calls = 0
        self._record_kill = record_kill if record_kill is not None else []
        self.returncode = None

    def communicate(self, input=None, timeout=None):  # noqa: A002, ARG002
        self._communicate_calls += 1
        if self._raise_timeout and self._communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="claude", timeout=timeout or 0)
        # Post-kill drain returns whatever we were configured with.
        self.returncode = self._returncode
        return self._stdout, self._stderr

    def kill(self) -> None:
        self._record_kill.append(True)


def _patch_popen(monkeypatch, *, popen):
    """Patch the analyzer's Popen so tests don't spawn real processes."""
    monkeypatch.setattr(_analyzer.subprocess, "Popen", lambda *a, **kw: popen)


_OK_JSON = (
    '{"difficulty_score": 5, "difficulty_label": "medium", '
    '"risk_score": 4, "risk_label": "moderate", '
    '"complexity_factors": [], "recommended_model": "balanced-code-model", '
    '"recommended_model_reason": "ok", '
    '"estimated_input_tokens": 1000, "estimated_output_tokens": 500, '
    '"estimated_cost_min": 0.01, "estimated_cost_max": 0.02, '
    '"cost_currency": "USD", "cost_estimate_status": "estimated", '
    '"queue_rank": 50, "queue_reason": "", "dependency_hints": [], '
    '"parallel_safe_candidate": false, '
    '"requires_human_plan_review": false, "human_plan_review_reason": null, '
    '"requires_human_code_review": false, "human_code_review_reason": null, '
    '"autonomous_execution_recommendation": "safe", '
    '"analysis_summary": "ok"}'
)


# ── T206 cases retained — now over the Popen-based path ──────────────────────


def test_subprocess_timeout_persists_failed(db: Path, tmp_path: Path, monkeypatch) -> None:
    fake = _FakePopen(raise_timeout=True, returncode=-9)
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "timed out" in (row["analysis_summary"] or "").lower()
    assert row["stage"] == "failed"
    failed_events = [
        e for e in _db.list_runtime_events(db, ticket_id="T001")
        if e["event_type"] == "ticket_intelligence_analysis_failed"
    ]
    assert failed_events, "expected a ticket_intelligence_analysis_failed runtime event"
    metadata = json.loads(failed_events[0]["metadata_json"])
    assert metadata.get("stage") == "waiting_ai"
    assert metadata.get("failure_origin") == "timeout"


def test_subprocess_nonzero_rc_persists_failed(db: Path, tmp_path: Path, monkeypatch) -> None:
    fake = _FakePopen(returncode=2, stdout="", stderr="boom")
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "rc=2" in (row["analysis_summary"] or "")
    assert row["failure_origin"] == "nonzero_rc"
    assert row["stage"] == "failed"
    failed_events = [
        e for e in _db.list_runtime_events(db, ticket_id="T001")
        if e["event_type"] == "ticket_intelligence_analysis_failed"
    ]
    assert failed_events
    metadata = json.loads(failed_events[0]["metadata_json"])
    assert metadata.get("stage") == "waiting_ai"
    assert metadata.get("failure_origin") == "nonzero_rc"


def test_subprocess_invalid_json_persists_failed(db: Path, tmp_path: Path, monkeypatch) -> None:
    fake = _FakePopen(returncode=0, stdout="not a json blob at all", stderr="")
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "json parse" in (row["analysis_summary"] or "").lower()
    assert row["failure_origin"] == "json_parse"
    assert row["stage"] == "failed"
    failed_events = [
        e for e in _db.list_runtime_events(db, ticket_id="T001")
        if e["event_type"] == "ticket_intelligence_analysis_failed"
    ]
    assert failed_events
    metadata = json.loads(failed_events[0]["metadata_json"])
    assert metadata.get("stage") == "parsing_result"
    assert metadata.get("failure_origin") == "json_parse"


def test_run_analysis_accepts_project_id_kwarg(db: Path, tmp_path: Path, monkeypatch) -> None:
    fake = _FakePopen(returncode=1, stdout="", stderr="forced fail")
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(
        db, "T001", "ticket body", "claude --skip", tmp_path,
        project_id="P1",
    )
    row = _db.get_ticket_intelligence(db, "T001")
    assert row["analysis_status"] == "failed"


# ── T208 — new lifecycle / hardening cases ──────────────────────────────────


def test_completed_persists_completed_at(db: Path, tmp_path: Path, monkeypatch) -> None:
    fake = _FakePopen(returncode=0, stdout=_OK_JSON, stderr="")
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "completed"
    assert row["completed_at"] is not None
    # started_at set when the row transitioned to running.
    assert row["started_at"] is not None
    assert row["failed_at"] is None
    assert row["failure_origin"] is None


def test_timeout_uses_kill_and_persists_failed_at(db: Path, tmp_path: Path, monkeypatch) -> None:
    record_kill: list = []
    fake = _FakePopen(raise_timeout=True, returncode=-9, record_kill=record_kill)
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    assert record_kill == [True]
    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert row["failure_origin"] == "timeout"
    assert row["failed_at"] is not None


def test_unexpected_exception_in_extract_persists_failed(db: Path, tmp_path: Path, monkeypatch) -> None:
    def _boom(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("extract_signals exploded")

    monkeypatch.setattr(_analyzer, "extract_signals", _boom)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert row["failure_origin"] == "exception"
    assert "extract_signals exploded" in (row["analysis_summary"] or "")
    assert row["failed_at"] is not None
    assert row["stage"] == "failed"
    failed_events = [
        e for e in _db.list_runtime_events(db, ticket_id="T001")
        if e["event_type"] == "ticket_intelligence_analysis_failed"
    ]
    assert failed_events
    metadata = json.loads(failed_events[0]["metadata_json"])
    # extract_signals runs before any explicit stage transition, while
    # current_stage is still STAGE_STARTING.
    assert metadata.get("stage") == "starting"
    assert metadata.get("failure_origin") == "exception"
    assert "traceback" in metadata


def test_finally_guard_marks_running_row_failed(db: Path, tmp_path: Path, monkeypatch) -> None:
    """A BaseException escaping the inner try/except must still leave a terminal row."""
    fake = _FakePopen(returncode=0, stdout=_OK_JSON, stderr="")
    _patch_popen(monkeypatch, popen=fake)

    def _explode(*args, **kwargs):  # noqa: ARG001
        # KeyboardInterrupt is a BaseException — bypasses the broad except clause.
        raise KeyboardInterrupt("simulated interruption inside _normalize")

    monkeypatch.setattr(_analyzer, "_normalize", _explode)

    with pytest.raises(KeyboardInterrupt):
        _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert row["failure_origin"] == "finally_guard"
    assert "without terminal status" in (row["analysis_summary"] or "")
    assert row["stage"] == "failed"


def test_stage_progresses_through_lifecycle_on_success(
    db: Path, tmp_path: Path, monkeypatch
) -> None:
    """A successful run records stage transitions in runtime_events and ends with stage=completed."""
    fake = _FakePopen(returncode=0, stdout=_OK_JSON, stderr="")
    _patch_popen(monkeypatch, popen=fake)

    _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "completed"
    assert row["stage"] == "completed"

    events = _db.list_runtime_events(db, ticket_id="T001")
    # list_runtime_events returns most-recent-first; reverse to get insertion order.
    stage_transitions = [
        json.loads(e["metadata_json"])["to"]
        for e in reversed(events)
        if e["event_type"] == "ticket_intelligence_stage_changed"
    ]
    expected = [
        "starting",
        "building_prompt",
        "waiting_ai",
        "parsing_result",
        "persisting",
        "completed",
    ]
    assert stage_transitions == expected

    event_types_in_order = [e["event_type"] for e in reversed(events)]
    assert "ticket_intelligence_analysis_started" in event_types_in_order
    assert "ticket_intelligence_ai_process_started" in event_types_in_order
    assert "ticket_intelligence_ai_process_completed" in event_types_in_order
    assert "ticket_intelligence_analysis_completed" in event_types_in_order
