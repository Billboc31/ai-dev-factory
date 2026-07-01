"""Daemon integration tests for poll_ticket_pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import main, poll_ticket_pipeline


def test_poll_ticket_pipeline_skips_when_disabled(tmp_path, monkeypatch, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    db_path = tmp_path / "fake.sqlite"

    with patch("run_daemon._is_auto_pipeline_enabled", return_value=False), \
         patch("run_daemon._init_pipeline_pools") as mock_init:
        poll_ticket_pipeline(
            db_path, runs, None, tmp_path, "claude --print", project_id="proj-a",
        )

    mock_init.assert_not_called()


def test_main_calls_poll_ticket_pipeline_each_cycle(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon._check_runtime_clone", return_value=True):
        with patch("run_daemon.poll_ticket_pipeline") as mock_pipeline:
            with patch("run_daemon.run_once"):
                rc = main([
                    "--exec-cmd", "test-cmd",
                    "--once",
                    "--runs-dir", str(runs),
                ])

    assert rc == 0
    mock_pipeline.assert_called_once()
