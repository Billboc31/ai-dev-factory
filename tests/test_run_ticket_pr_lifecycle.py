"""Tests for PR lifecycle at the end of run_ticket --auto."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))

import run_ticket as rt  # noqa: E402


def _init_state(tmp_path: Path, ticket_id: str, state: str, **extra) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    payload = {
        "ticket_id": ticket_id,
        "state": state,
        "branch": f"ticket/{ticket_id}-feature",
        "issue_number": 42,
        **extra,
    }
    (run_dir / "state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_finalize_test_complete_pr_skips_when_issue_closed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_state(tmp_path, "T001", "TEST_COMPLETE", issue_closed=True)

    with patch("ticket_pr_lifecycle.handle_test_complete") as mock_handle:
        rt._finalize_test_complete_pr("T001")

    mock_handle.assert_not_called()


def test_finalize_test_complete_pr_invokes_shared_handler(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_state(tmp_path, "T001", "TEST_COMPLETE")

    with patch("ticket_pr_lifecycle.handle_test_complete") as mock_handle, \
         patch.object(rt, "_resolve_github_repo", return_value="org/repo"):
        rt._finalize_test_complete_pr("T001")

    mock_handle.assert_called_once()
    args, kwargs = mock_handle.call_args
    assert args[0] == "T001"
    assert args[2] == "org/repo"
    assert kwargs["worktree_cwd"] == str(tmp_path)


def test_auto_run_retries_pr_finalize_when_already_test_complete(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_state(tmp_path, "T001", "TEST_COMPLETE")

    with patch.object(rt, "_finalize_test_complete_pr") as mock_finalize:
        rc = rt.auto_run("T001", "claude -p")

    assert rc == 0
    mock_finalize.assert_called_once_with("T001")
