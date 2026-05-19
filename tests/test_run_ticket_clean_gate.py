"""Tests for the clean gate in `run_ticket._check_working_tree_clean`.

The gate must:
  - PASS when only runtime/generated files are dirty (runs/<ticket>/runtime.log,
    __pycache__/*.pyc, runs/.project-map*.json, runs/daemon.log, .runtime/*.sqlite, ...)
  - BLOCK as soon as any *real* source-tree file is dirty
  - PASS unchanged when the working tree is already clean
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import TicketRunnerError, _check_working_tree_clean


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ── clean tree: no-op ────────────────────────────────────────────────────────


def test_clean_gate_passes_when_already_clean() -> None:
    with patch("run_ticket.run_command", return_value=_cp(stdout="")):
        _check_working_tree_clean()  # must not raise


# ── only ticket runtime.log dirty: must pass ─────────────────────────────────


def test_clean_gate_passes_when_only_ticket_runtime_log_dirty(capsys) -> None:
    porcelain = " M runs/T099/runtime.log\n"
    with patch("run_ticket.run_command", return_value=_cp(stdout=porcelain)):
        _check_working_tree_clean()  # must not raise

    out = capsys.readouterr().out
    assert "clean gate: ignored runtime dirty files" in out
    assert "runs/T099/runtime.log" in out


# ── all categories of ignorable runtime files: must pass ─────────────────────


def test_clean_gate_passes_for_all_ignorable_categories(capsys) -> None:
    porcelain = (
        " M runs/T099/runtime.log\n"
        " M runs/daemon.log\n"
        " M runs/.project-map.json\n"
        " M runs/.project-map-activity.json\n"
        " M tools/agent_runner/__pycache__/run_ticket.cpython-314.pyc\n"
        " M .runtime/ai-dev-factory.sqlite\n"
    )
    with patch("run_ticket.run_command", return_value=_cp(stdout=porcelain)):
        _check_working_tree_clean()  # must not raise

    assert "clean gate: ignored runtime dirty files" in capsys.readouterr().out


# ── real source change: must block ───────────────────────────────────────────


def test_clean_gate_blocks_real_code_change() -> None:
    porcelain = " M tools/agent_runner/run_ticket.py\n"
    with patch("run_ticket.run_command", return_value=_cp(stdout=porcelain)):
        with pytest.raises(TicketRunnerError, match="working tree is not clean"):
            _check_working_tree_clean()


def test_clean_gate_blocks_when_mixing_ignorable_and_real() -> None:
    """Any real dirty file must still trigger refusal even alongside runtime noise."""
    porcelain = (
        " M runs/T099/runtime.log\n"
        " M tools/agent_runner/run_ticket.py\n"
    )
    with patch("run_ticket.run_command", return_value=_cp(stdout=porcelain)):
        with pytest.raises(TicketRunnerError, match="working tree is not clean"):
            _check_working_tree_clean()


# ── git failure still raises ─────────────────────────────────────────────────


def test_clean_gate_raises_when_git_status_fails() -> None:
    with patch("run_ticket.run_command", return_value=_cp(returncode=1, stderr="boom")):
        with pytest.raises(TicketRunnerError, match="failed to check git status"):
            _check_working_tree_clean()
