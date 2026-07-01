"""T221 — atomic ``claim_readiness`` under concurrent workers."""

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
        "_runtime_db_sqlite_claim_ready",
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

pipeline.runtime_db = _db


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "claim_ready.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def test_single_worker_claims_fresh_ticket(db: Path):
    assert pipeline.claim_readiness(db, "T110") is True
    row = _db.get_ticket_readiness(db, "T110")
    assert row["readiness_status"] == "running"


def test_second_call_rejected_while_running(db: Path):
    assert pipeline.claim_readiness(db, "T111") is True
    assert pipeline.claim_readiness(db, "T111") is False


def test_ready_candidate_can_be_reclaimed(db: Path):
    _db.upsert_ticket_readiness(db, "T112", readiness_status="ready_candidate")
    # ``ready_candidate`` is not terminal from the claim helper's perspective:
    # re-evaluation is allowed when upstream data changes.
    assert pipeline.claim_readiness(db, "T112") is True


def test_two_workers_same_ticket_only_one_claims(db: Path):
    barrier = threading.Barrier(2)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        result = pipeline.claim_readiness(db, "T210")
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == [False, True]
    row = _db.get_ticket_readiness(db, "T210")
    assert row["readiness_status"] == "running"
