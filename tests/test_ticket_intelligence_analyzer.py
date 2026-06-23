"""Tests for ticket_intelligence_analyzer subprocess failure handling (T206)."""

from __future__ import annotations

import importlib.util
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


def test_subprocess_timeout_persists_failed(db: Path, tmp_path: Path) -> None:
    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0] if args else "claude", timeout=120)

    with patch.object(_analyzer.subprocess, "run", side_effect=_raise_timeout):
        _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "timed out" in (row["analysis_summary"] or "").lower()


def test_subprocess_nonzero_rc_persists_failed(db: Path, tmp_path: Path) -> None:
    fake_proc = subprocess.CompletedProcess(
        args=["claude"], returncode=2, stdout="", stderr="boom"
    )
    with patch.object(_analyzer.subprocess, "run", return_value=fake_proc):
        _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "rc=2" in (row["analysis_summary"] or "")


def test_subprocess_invalid_json_persists_failed(db: Path, tmp_path: Path) -> None:
    fake_proc = subprocess.CompletedProcess(
        args=["claude"], returncode=0, stdout="not a json blob at all", stderr=""
    )
    with patch.object(_analyzer.subprocess, "run", return_value=fake_proc):
        _analyzer.run_analysis(db, "T001", "ticket body", "claude --skip", tmp_path)

    row = _db.get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "failed"
    assert "json parse" in (row["analysis_summary"] or "").lower()


def test_run_analysis_accepts_project_id_kwarg(db: Path, tmp_path: Path) -> None:
    """project_id is accepted (for log correlation) without changing behavior."""
    fake_proc = subprocess.CompletedProcess(
        args=["claude"], returncode=1, stdout="", stderr="forced fail"
    )
    with patch.object(_analyzer.subprocess, "run", return_value=fake_proc):
        _analyzer.run_analysis(
            db, "T001", "ticket body", "claude --skip", tmp_path,
            project_id="P1",
        )
    row = _db.get_ticket_intelligence(db, "T001")
    assert row["analysis_status"] == "failed"
