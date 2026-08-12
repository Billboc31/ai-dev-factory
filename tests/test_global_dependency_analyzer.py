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


def _seed_batch_with_bodies(
    db: Path, runs_dir: Path, ticket_bodies: dict[str, str],
) -> str:
    """Like ``_seed_batch_with_tickets`` but lets each ticket carry a specific body."""
    batch_id = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    for tid, body in ticket_bodies.items():
        run_dir = runs_dir / tid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "ticket.md").write_text(f"# {tid}\n\n{body}\n", encoding="utf-8")
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


# ── Coherence pass tests (T220) ───────────────────────────────────────────────


def test_conflicting_scope_relationship_populates_conflicting_tickets(
    db, runs_dir, monkeypatch,
):
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "architecture and product vision",
        "T010": "project foundation and baseline documentation",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [
            {"from": "T001", "to": "T010", "type": "CONFLICTING_SCOPE"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t001["conflicting_tickets"] == ["T010"]
    assert row_t010["conflicting_tickets"] == ["T001"]


def test_foundation_b_track_depends_on_foundation_a_vision(db, runs_dir, monkeypatch):
    """foundation-b baseline docs must depend on foundation-a vision/arch anchor."""
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": (
            "Define product vision, scope, and architecture for the project. "
            "Establish the technical stack."
        ),
        "T010": (
            "Establish project foundation and baseline documentation. "
            "Confirm the product vision. README and global-context docs."
        ),
        "T011": "Bootstrap backend express typescript foundation",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": ["T002"],
                "parallel_group": "foundation-a",
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": ["T011"],
                "parallel_group": "foundation-b",
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
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t001["depends_on"] == []
    assert row_t010["depends_on"] == ["T001"]
    assert int(row_t010["execution_phase"]) > int(row_t001["execution_phase"])
    rel_types = {r["type"] for r in row_t010["relationship_classifications"]}
    assert "FOUNDATION_DEPENDENCY" in rel_types


def test_foundation_baseline_text_without_parallel_group_depends_on_vision(
    db, runs_dir, monkeypatch,
):
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "Product vision and system architecture",
        "T010": "Baseline documentation and README for local development",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t010["depends_on"] == ["T001"]


def test_conflicting_pair_gets_split_across_phases(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "architecture and technical stack",
        "T010": "backend api service for orders",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T010"],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T001"],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t001["execution_phase"] != row_t010["execution_phase"]


def test_phase_is_recomputed_when_dependency_ordering_violated(
    db, runs_dir, monkeypatch,
):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 3,
            },
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
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    row_t011 = _db.get_dependency_analysis(db, "T011", batch_id)
    assert int(row_t011["execution_phase"]) > int(row_t010["execution_phase"])


def test_foundation_ticket_lands_in_earliest_phase(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "product architecture and coding conventions",
        "T010": "backend api service for orders",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 2,
            },
            {
                "ticket_id": "T010",
                "depends_on": ["T001"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 5,
            },
        ],
        "relationships": [
            {"from": "T010", "to": "T001", "type": "FOUNDATION_DEPENDENCY"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    assert row_t001["execution_phase"] == "1"
    assert row_t010["execution_phase"] == "2"


def test_cycle_is_broken_without_failure(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T001", "T002"])
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": ["T002"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T002",
                "depends_on": ["T001"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t002 = _db.get_dependency_analysis(db, "T002", batch_id)
    assert row_t001 is not None and row_t002 is not None
    # At most one direction of the edge may survive
    has_forward = "T002" in row_t001["depends_on"]
    has_backward = "T001" in row_t002["depends_on"]
    assert not (has_forward and has_backward)


def test_conflict_foundation_vs_bootstrap_bumps_bootstrap(
    db, runs_dir, monkeypatch,
):
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "architecture and technical stack decisions",
        "T002": "bootstrap the repository scaffold",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T002"],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T002",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T001"],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_t001 = _db.get_dependency_analysis(db, "T001", batch_id)
    row_t002 = _db.get_dependency_analysis(db, "T002", batch_id)
    assert row_t001["execution_phase"] == "1"
    assert int(row_t002["execution_phase"]) > int(row_t001["execution_phase"])


def test_conflict_backend_vs_frontend_bumps_frontend_when_frontend_consumes_backend(
    db, runs_dir, monkeypatch,
):
    # Numerical id ordering would place T010 before T020; the test flips that
    # so the fallback (ticket_id) never becomes load-bearing.
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T050": "backend service endpoint for orders",
        "T020": "frontend dashboard page component",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T050",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T020"],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T020",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T050"],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True
    row_backend = _db.get_dependency_analysis(db, "T050", batch_id)
    row_frontend = _db.get_dependency_analysis(db, "T020", batch_id)
    assert int(row_frontend["execution_phase"]) > int(row_backend["execution_phase"])


def test_conflict_ticket_id_fallback_only_when_ties():
    """When roles and original phases tie, the larger ticket id is bumped."""
    # Case A: larger id is T200
    norm_tickets_a = [
        {
            "ticket_id": "T100",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": ["T200"],
            "execution_phase": "1",
        },
        {
            "ticket_id": "T200",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": ["T100"],
            "execution_phase": "1",
        },
    ]
    _, _, notes_a = gda._enforce_coherence(
        norm_tickets_a,
        [],
        {"T100": 1, "T200": 1},
        {"T100": "generic misc body", "T200": "generic misc body"},
    )
    phases_a = {t["ticket_id"]: int(t["execution_phase"]) for t in norm_tickets_a}
    assert phases_a["T100"] == 1
    assert phases_a["T200"] == 2
    assert any("ticket_id" in n for n in notes_a)

    # Case B: swap ids — the smaller one (A010) must be kept
    norm_tickets_b = [
        {
            "ticket_id": "A050",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": ["A010"],
            "execution_phase": "1",
        },
        {
            "ticket_id": "A010",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": ["A050"],
            "execution_phase": "1",
        },
    ]
    _, _, notes_b = gda._enforce_coherence(
        norm_tickets_b,
        [],
        {"A050": 1, "A010": 1},
        {"A050": "generic misc body", "A010": "generic misc body"},
    )
    phases_b = {t["ticket_id"]: int(t["execution_phase"]) for t in norm_tickets_b}
    assert phases_b["A010"] == 1
    assert phases_b["A050"] == 2
    assert any("ticket_id" in n for n in notes_b)


# ── Reasoning-summary tests (T222) ────────────────────────────────────────────


def _reasoning_payload() -> str:
    """LLM response with full reasoning fields populated."""
    return json.dumps({
        "analysis_summary": {
            "strategy": "Foundation first, then backend, then frontend.",
            "foundation_tickets": ["T010"],
            "bootstrap_tickets": [],
            "important_inferred_dependencies": [
                "T011 depends on T010 (backend API contract).",
            ],
            "parallel_opportunities": [],
            "conflicts_resolved": [],
            "warnings": ["T010 body is thin — best-effort inference."],
        },
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": ["T011"],
                "parallel_group": "foundation",
                "conflicting_tickets": [],
                "execution_phase": 1,
                "why_this_phase": "Architectural foundation everything depends on.",
                "dependencies_inferred": [],
                "reasoning": "Foundation ticket — must land first.",
                "confidence": "high",
            },
            {
                "ticket_id": "T011",
                "depends_on": ["T010"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 2,
                "why_this_phase": "Builds on T010's contract.",
                "dependencies_inferred": [
                    "T010 — provides the API contract T011 consumes.",
                ],
                "reasoning": "Backend API consumer of T010.",
                "confidence": "medium",
            },
        ],
        "relationships": [
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
        ],
    })


def test_normalize_response_extracts_reasoning_fields():
    raw = json.loads(_reasoning_payload())
    summary, tickets, _ = gda._normalize_response(raw)
    assert summary["strategy"].startswith("Foundation first")
    assert summary["foundation_tickets"] == ["T010"]
    assert summary["warnings"] == ["T010 body is thin — best-effort inference."]

    by_id = {t["ticket_id"]: t for t in tickets}
    assert by_id["T011"]["why_this_phase"] == "Builds on T010's contract."
    assert by_id["T011"]["dependencies_inferred"] == [
        "T010 — provides the API contract T011 consumes.",
    ]
    assert by_id["T011"]["reasoning"] == "Backend API consumer of T010."
    assert by_id["T011"]["confidence"] == "medium"


def test_normalize_response_defaults_missing_reasoning_fields():
    raw = {
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
                # Reasoning fields intentionally omitted.
            },
        ],
        "relationships": [],
    }
    summary, tickets, _ = gda._normalize_response(raw)
    assert summary == {}
    t = tickets[0]
    assert t["why_this_phase"] is None
    assert t["dependencies_inferred"] == []
    assert t["reasoning"] is None
    assert t["confidence"] is None


def test_normalize_response_malformed_reasoning_fields_are_safe():
    raw = {
        "analysis_summary": "not a dict",  # malformed
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
                "why_this_phase": 42,  # not a string
                "dependencies_inferred": "oops",  # not a list
                "reasoning": None,
                "confidence": "medium-ish",  # not one of low/medium/high
            },
        ],
        "relationships": [],
    }
    summary, tickets, _ = gda._normalize_response(raw)
    assert summary == {}
    t = tickets[0]
    assert t["why_this_phase"] is None
    assert t["dependencies_inferred"] == []
    assert t["reasoning"] is None
    assert t["confidence"] is None


def test_reasoning_persisted_on_upsert(db, runs_dir, monkeypatch):
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    _configure_stub(monkeypatch, stdout=_reasoning_payload())
    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    )
    assert outcome.success is True

    row_t011 = _db.get_dependency_analysis(db, "T011", batch_id)
    assert row_t011["why_this_phase"] == "Builds on T010's contract."
    assert row_t011["dependencies_inferred"] == [
        "T010 — provides the API contract T011 consumes.",
    ]
    assert row_t011["reasoning"] == "Backend API consumer of T010."
    assert row_t011["confidence"] == "medium"

    batch_summary = _db.get_batch_analysis_summary(db, batch_id)
    assert batch_summary is not None
    assert batch_summary["analysis_summary"]["strategy"].startswith("Foundation")
    assert batch_summary["analysis_summary"]["foundation_tickets"] == ["T010"]
    raw = batch_summary["raw_analyzer_output"]
    assert isinstance(raw, dict)
    assert "parsed" in raw
    assert "stdout_excerpt" in raw
    assert batch_summary["generated_at"] is not None


def test_reasoning_survives_coherence_pass(db, runs_dir, monkeypatch):
    """Coherence bumps a phase; the per-ticket reasoning stays as returned."""
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010", "T011"])
    payload = json.dumps({
        "analysis_summary": {"strategy": "s"},
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 3,  # will be moved to 1 by coherence
                "why_this_phase": "written by the LLM",
                "dependencies_inferred": [],
                "reasoning": "foundation",
                "confidence": "high",
            },
            {
                "ticket_id": "T011",
                "depends_on": ["T010"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,  # coherence will bump to 2
                "why_this_phase": "consumer",
                "dependencies_inferred": ["T010 — provides X"],
                "reasoning": "backend consumer",
                "confidence": "low",
            },
        ],
        "relationships": [
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    )
    assert outcome.success is True
    row_t010 = _db.get_dependency_analysis(db, "T010", batch_id)
    row_t011 = _db.get_dependency_analysis(db, "T011", batch_id)
    # phase moved but reasoning preserved verbatim.
    assert row_t010["why_this_phase"] == "written by the LLM"
    assert row_t011["reasoning"] == "backend consumer"
    assert row_t011["confidence"] == "low"


def test_missing_analysis_summary_still_persists_raw_output(db, runs_dir, monkeypatch):
    """The LLM omits ``analysis_summary`` — raw output still lands so operators can debug."""
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010"])
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    )
    assert outcome.success is True
    summary = _db.get_batch_analysis_summary(db, batch_id)
    assert summary is not None
    assert summary["analysis_summary"] == {}
    assert summary["raw_analyzer_output"] is not None


def test_raw_stdout_excerpt_is_truncated(db, runs_dir, monkeypatch):
    """The stdout_excerpt is capped so a chatty LLM cannot bloat the DB row."""
    batch_id = _seed_batch_with_tickets(db, runs_dir, ["T010"])
    # Pad the JSON with a giant trailing comment-like blob so the raw stdout
    # exceeds the 20 000 char cap. The extractor still finds the JSON object.
    padding = "X" * 25_000
    payload_json = json.dumps({
        "tickets": [
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 1,
            },
        ],
        "relationships": [],
    })
    stdout = f"{payload_json}\n\n{padding}"
    _configure_stub(monkeypatch, stdout=stdout)
    outcome = gda.run_global_analysis(
        db, runs_dir, batch_id, exec_cmd="echo fake",
    )
    assert outcome.success is True
    summary = _db.get_batch_analysis_summary(db, batch_id)
    assert summary is not None
    excerpt = summary["raw_analyzer_output"]["stdout_excerpt"]
    assert len(excerpt) <= gda._RAW_STDOUT_MAX_CHARS


def test_realistic_test_ai_dev_backlog(db, runs_dir, monkeypatch):
    """The `test-ai-dev` bad-case: T001 (architecture) shares phase 1 with T010 (backend)
    while being marked as conflicting. Coherence must lift T010 into a later phase
    via role ordering (not ticket-id fallback)."""
    batch_id = _seed_batch_with_bodies(db, runs_dir, {
        "T001": "product vision, architecture and coding conventions",
        "T002": "bootstrap the project scaffold",
        "T010": "backend api service endpoint for orders",
        "T011": "backend api endpoint for products",
        "T020": "frontend dashboard page component",
        "T030": "integration wiring between backend and frontend",
    })
    payload = json.dumps({
        "tickets": [
            {
                "ticket_id": "T001",
                "depends_on": [],
                "blocks": [],
                "parallel_group": "foundation",
                "conflicting_tickets": ["T010"],
                "execution_phase": 1,
            },
            {
                "ticket_id": "T002",
                "depends_on": ["T001"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 2,
            },
            {
                "ticket_id": "T010",
                "depends_on": [],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": ["T001"],
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
            {
                "ticket_id": "T020",
                "depends_on": ["T011"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 3,
            },
            {
                "ticket_id": "T030",
                "depends_on": ["T020", "T011"],
                "blocks": [],
                "parallel_group": None,
                "conflicting_tickets": [],
                "execution_phase": 4,
            },
        ],
        "relationships": [
            {"from": "T002", "to": "T001", "type": "FOUNDATION_DEPENDENCY"},
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
            {"from": "T020", "to": "T011", "type": "HARD_DEPENDENCY"},
            {"from": "T030", "to": "T020", "type": "HARD_DEPENDENCY"},
            {"from": "T030", "to": "T011", "type": "HARD_DEPENDENCY"},
        ],
    })
    _configure_stub(monkeypatch, stdout=payload)
    outcome = gda.run_global_analysis(db, runs_dir, batch_id, exec_cmd="echo fake")
    assert outcome.success is True

    rows = {tid: _db.get_dependency_analysis(db, tid, batch_id) for tid in [
        "T001", "T002", "T010", "T011", "T020", "T030",
    ]}
    phases = {tid: int(r["execution_phase"]) for tid, r in rows.items()}

    # T001 is alone in phase 1
    assert phases["T001"] == 1
    for other in ("T002", "T010", "T011", "T020", "T030"):
        assert phases[other] > phases["T001"], f"{other} not later than T001"

    # No conflicting pair shares a phase
    for tid, row in rows.items():
        for c in row["conflicting_tickets"]:
            if c in rows:
                assert phases[tid] != phases[c]

    # The T001↔T010 split was resolved by the `role` step, not `ticket_id`
    norm_tickets_direct = []
    for tid in ["T001", "T002", "T010", "T011", "T020", "T030"]:
        r = rows[tid]
        norm_tickets_direct.append({
            "ticket_id": tid,
            "depends_on": list(r["depends_on"]),
            "blocks": list(r["blocks"]),
            "parallel_group": r["parallel_group"],
            "conflicting_tickets": list(r["conflicting_tickets"]),
            "execution_phase": r["execution_phase"],
        })
    # Reconstruct a same-phase conflict scenario by replaying the input directly
    replay_tickets = json.loads(payload)["tickets"]
    replay_relationships = json.loads(payload)["relationships"]
    original_phases_snapshot = {
        t["ticket_id"]: int(t["execution_phase"]) for t in replay_tickets
    }
    ticket_texts = {
        "T001": "product vision, architecture and coding conventions",
        "T002": "bootstrap the project scaffold",
        "T010": "backend api service endpoint for orders",
        "T011": "backend api endpoint for products",
        "T020": "frontend dashboard page component",
        "T030": "integration wiring between backend and frontend",
    }
    _, _, notes = gda._enforce_coherence(
        [dict(t, execution_phase=str(t["execution_phase"])) for t in replay_tickets],
        replay_relationships,
        original_phases_snapshot,
        ticket_texts,
    )
    resolver_step_note = next(
        (n for n in notes if n.startswith("resolver_steps=")), None,
    )
    assert resolver_step_note is not None
    assert "'role'" in resolver_step_note
    assert "'ticket_id'" not in resolver_step_note


def test_coherence_serializes_migration_writers_into_distinct_phases():
    tickets = [
        {
            "ticket_id": "T020",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": [],
            "execution_phase": "2",
        },
        {
            "ticket_id": "T023",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": [],
            "execution_phase": "2",
        },
        {
            "ticket_id": "T030",
            "depends_on": [],
            "blocks": [],
            "parallel_group": None,
            "conflicting_tickets": [],
            "execution_phase": "2",
        },
    ]
    texts = {
        "T020": "Add drizzle migration for release lifecycle under apps/api/migrations/.",
        "T023": "Add drizzle migration for plex source type.",
        "T030": "Build a React settings page with no schema changes.",
    }
    out_tickets, out_rels, notes = gda._enforce_coherence(
        tickets,
        [],
        {"T020": 2, "T023": 2, "T030": 2},
        texts,
    )
    by_id = {t["ticket_id"]: t for t in out_tickets}
    assert by_id["T020"]["execution_phase"] != by_id["T023"]["execution_phase"]
    assert any(n.startswith("migration_writers_serialized=") for n in notes)
    assert by_id["T020"]["parallel_group"] == "schema-migration-exclusive"
    assert by_id["T023"]["parallel_group"] == "schema-migration-exclusive"
    assert any(r["type"] == "CONFLICTING_SCOPE" for r in out_rels)
