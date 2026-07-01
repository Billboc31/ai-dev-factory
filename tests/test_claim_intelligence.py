"""T221 — atomic ``claim_intelligence`` under concurrent workers."""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_claim_intel",
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

# Bind ticket_pipeline.runtime_db to the isolated sqlite loader so the claim
# helper writes to the same DB file the test set up. Without this rebinding
# the helper would open the process-default backend and skip our fixture.
pipeline.runtime_db = _db


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "claim_intel.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def test_single_worker_claims_fresh_ticket(db: Path):
    assert pipeline.claim_intelligence(db, "T100") is True
    row = _db.get_ticket_intelligence(db, "T100")
    assert row["analysis_status"] == "running"


def test_second_call_is_rejected_while_running(db: Path):
    assert pipeline.claim_intelligence(db, "T101") is True
    assert pipeline.claim_intelligence(db, "T101") is False


def test_completed_ticket_cannot_be_reclaimed(db: Path):
    _db.upsert_ticket_intelligence(db, "T102", analysis_status="completed")
    assert pipeline.claim_intelligence(db, "T102") is False


def test_failed_ticket_can_be_reclaimed(db: Path):
    _db.upsert_ticket_intelligence(db, "T103", analysis_status="failed")
    assert pipeline.claim_intelligence(db, "T103") is True


def test_two_workers_same_ticket_only_one_claims(db: Path):
    barrier = threading.Barrier(2)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        result = pipeline.claim_intelligence(db, "T200")
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == [False, True]
    row = _db.get_ticket_intelligence(db, "T200")
    assert row["analysis_status"] == "running"
