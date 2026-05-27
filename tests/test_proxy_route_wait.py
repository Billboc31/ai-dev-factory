"""Tests for _wait_for_proxy_url in run_sandbox."""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_sandbox


def test_wait_returns_true_when_traefik_responds(tmp_path):
    log = tmp_path / "run.log"
    log.write_text("")

    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
        url=None, code=503, msg="Service Unavailable", hdrs=None, fp=None
    )):
        result = run_sandbox._wait_for_proxy_url("abc123", log, timeout_s=1)

    assert result is True
    assert "proxy: route active" in log.read_text()


def test_wait_returns_false_on_connection_error(tmp_path):
    log = tmp_path / "run.log"
    log.write_text("")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = run_sandbox._wait_for_proxy_url("abc123", log, timeout_s=2)

    assert result is False


def test_wait_logs_infra_failure(tmp_path):
    log = tmp_path / "run.log"
    log.write_text("")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        run_sandbox._wait_for_proxy_url("abc123", log, timeout_s=2)

    assert "proxy: infra unreachable after 2s" in log.read_text()
