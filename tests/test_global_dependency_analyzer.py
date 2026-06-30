"""Tests for the global dependency analyzer (T218)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_gda",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()


def _load_backlog_batch():
    name = "_backlog_batch_for_gda"
    spec = importlib.util.spec_from_file_location(name, _TOOLS / "backlog_batch.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.runtime_db = _db
    return mod


def _load_analyzer():
    name = "_global_dependency_analyzer_under_test"
    spec = importlib.util.spec_from_file_location(name, _TOOLS / "global_dependency_analyzer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.runtime_db = _db
    return mod


bb = _load_backlog_batch()
gda = _load_analyzer()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / ".runtime" / "gda.sqlite"
    _db.init_runtime_db(path)
    return path


@pytest.fixture()
def runs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "runs"
    d.mkdir()
    return d


def _seed_batch_with_tickets(db: Path, runs_dir: Path, ticket_ids: list[str]) -> str:
    batch_id = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    for tid in ticket_ids:
        run_dir = runs_dir / tid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "ticket.md").write_text(f"# {tid}\n\nbody for {tid}\n", encoding="utf-8")
        bb.add_ticket_to_batch(db, batch_id, tid)
    return batch_id


def _well_formed_json() -> str:
    return json.dumps({
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": ["T011"],
                "parallel_group": "foundation",
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T011",
                "depends_on": ["T010"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 2,
            },
        ],
        "relationships": [
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
        ],
    })


class _StubPopen:
    instance = None

    def __init__(self, *_args, **_kwargs):
        type(self).instance = self
        self._stdout = type(self)._stdout
        self._stderr = type(self)._stderr
        self._rc = type(self)._rc
        self.returncode = None

    def communicate(self, input=None, timeout=None):
        self.returncode = self._rc
        return self._stdout, self._stderr

    def kill(self):
        self.returncode = -9


def _configure_stub(monkeypatch, *, stdout: str, stderr: str = "", rc: int = 0):
    _StubPopen._stdout = stdout
    _StubPopen._stderr = stderr
    _StubPopen._rc = rc
    monkeypatch.setattr(gda.subprocess, "Popen", _StubPopen)


def test_well_formed_response_persists_rows(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    _configure_stub(monkeypatch, stdout=_well_formed_json())

    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id,
        exec_cmd="echo fake", timeout_seconds=30,
    )
    assert outcome.success is True
    assert outcome.persisted_ticket_count == 2

    row_t011 = _db.get_dependency_analysis(db, "T011", batch_id)
    assert row_t011 is not None
    assert row_t011["depends_on"] == ["T010"]
    assert row_t011["execution_phase"] == "2"

    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t010 is not None
    assert row_t010["blocks"] == ["T011"]
    assert row_t010["parallel_group"] == "foundation"


def test_malformed_response_returns_failure(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010"])
    _configure_stub(monkeypatch, stdout="not json at all")

    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id,
        exec_cmd="echo fake", timeout_seconds=30,
    )
    assert outcome.success is False
    assert outcome.error is not None
    assert "JSON" in outcome.error or "json" in outcome.error
    assert _db.get_dependency_analysis(db, "T010", batch_id) is None


def test_nonzero_rc_returns_failure(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010"])
    _configure_stub(monkeypatch, stdout="", stderr="boom", rc=2)
    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake", timeout_seconds=30,
    )
    assert outcome.success is False


def test_retry_upserts_without_duplicates(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    _configure_stub(monkeypatch, stdout=_well_formed_json())

    assert gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    ).success is True
    assert gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    ).success is True

    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM ticket_dependency_analysis WHERE batch_id = ?",
            (batch_id,),
        )
        count = cur.fetchone()[0]
    assert count == 2


def test_invalid_relationship_type_dropped(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T011",
                "depends_on": ["T010"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [
            {"from": "T011", "to": "T010", "type": "NOT_REAL"},
            {"from": "T011", "to": "T010", "type": "SOFT_DEPENDENCY"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)

    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    )
    assert outcome.success is True
    row = _db.get_dependency_analysis(db, "T011", batch_id)
    assert row is not None
    rels = row["relationship_classifications"]
    types = {r["type"] for r in rels}
    assert types == {"SOFT_DEPENDENCY"}
