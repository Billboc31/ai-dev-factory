"""T221 — batch GitHub issue intake tests.

Cover the three scenarios exercised by the new poll flow:

- Discovering N issues intakes all N in a single poll.
- Repeating an already-seen issue on the next poll bumps ``skipped_existing``
  and does not create duplicate rows.
- Reaching ``MAX_ISSUES_INTAKED_PER_POLL`` caps the batch and reports
  ``skipped_limit`` for the deferred remainder.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import load_issue_index, poll_github_issues  # noqa: E402


def _make_runs(tmp_path: Path) -> Path:
    runs = tmp_path / "runs"
    runs.mkdir()
    return runs


def _issues(n: int) -> list[dict]:
    return [{"number": i, "title": f"Issue #{i}"} for i in range(1, n + 1)]


def _stub_intake_paths():
    """Return a stack of patches that neutralise all filesystem side-effects."""
    return [
        patch("run_daemon.call_issue_intake", return_value=True),
        patch(
            "run_daemon.fetch_origin_main",
            return_value=(True, "fetched origin/main"),
        ),
        patch(
            "run_daemon.create_ticket_branch_and_worktree",
            return_value=(True, "ok"),
        ),
        patch("run_daemon.clear_stale_run_dir", return_value=False),
    ]


def test_20_issues_discovered_one_poll(tmp_path, capsys, monkeypatch):
    runs = _make_runs(tmp_path)
    worktrees = tmp_path / "worktrees"
    monkeypatch.setenv("MAX_ISSUES_INTAKED_PER_POLL", "50")

    patches = _stub_intake_paths()
    with patch("run_daemon.fetch_ready_issues", return_value=_issues(20)):
        for p in patches:
            p.start()
        try:
            poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees)
        finally:
            for p in patches:
                p.stop()

    index = load_issue_index(runs)
    assert len(index) == 20
    for i in range(1, 21):
        assert str(i) in index

    out = capsys.readouterr().out
    assert "github poll: discovered=20 intaked=20" in out
    assert "skipped_existing=0" in out
    assert "skipped_limit=0" in out


def test_repeated_issue_is_idempotent(tmp_path, capsys, monkeypatch):
    runs = _make_runs(tmp_path)
    worktrees = tmp_path / "worktrees"
    monkeypatch.setenv("MAX_ISSUES_INTAKED_PER_POLL", "50")

    patches = _stub_intake_paths()
    with patch("run_daemon.fetch_ready_issues", return_value=_issues(1)):
        for p in patches:
            p.start()
        try:
            poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees)
            capsys.readouterr()  # discard first-poll noise
            poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees)
        finally:
            for p in patches:
                p.stop()

    index = load_issue_index(runs)
    assert index == {"1": "T001"}

    out = capsys.readouterr().out
    assert "github poll: discovered=1 intaked=0 skipped_existing=1" in out


def test_max_issues_intaked_per_poll_caps_batch(tmp_path, capsys, monkeypatch):
    runs = _make_runs(tmp_path)
    worktrees = tmp_path / "worktrees"
    monkeypatch.setenv("MAX_ISSUES_INTAKED_PER_POLL", "5")

    patches = _stub_intake_paths()
    with patch("run_daemon.fetch_ready_issues", return_value=_issues(12)):
        for p in patches:
            p.start()
        try:
            poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees)
        finally:
            for p in patches:
                p.stop()

    index = load_issue_index(runs)
    assert len(index) == 5

    out = capsys.readouterr().out
    assert "github poll: discovered=12 intaked=5" in out
    assert "skipped_limit=7" in out
