"""Unit tests for _parse_healthcheck_output in run_sandbox.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_sandbox  # noqa: E402


def _parse(stdout: str, stderr: str = "", exit_code: int = 0) -> dict:
    return run_sandbox._parse_healthcheck_output(stdout, stderr, exit_code)


def test_pass_probe_parsed():
    stdout = "PASS api (http://api.sandbox-foo.localhost) http=200\n"
    result = _parse(stdout)
    assert len(result["probes"]) == 1
    probe = result["probes"][0]
    assert probe["name"] == "api"
    assert probe["url"] == "http://api.sandbox-foo.localhost"
    assert probe["result"] == "pass"
    assert probe["http_code"] == "200"


def test_fail_probe_parsed():
    stdout = "FAIL web (http://sandbox-foo.localhost) http=000 — connection refused\n"
    result = _parse(stdout)
    probe = result["probes"][0]
    assert probe["result"] == "fail"
    assert probe["name"] == "web"
    assert probe["http_code"] == "000"
    assert "connection refused" in probe["note"]


def test_summary_line_sets_counts():
    stdout = (
        "PASS api (http://api.sandbox-foo.localhost) http=200\n"
        "FAIL web (http://sandbox-foo.localhost) http=000\n"
        "healthcheck: 1 passed, 1 failed\n"
    )
    result = _parse(stdout, exit_code=1)
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["exit_code"] == 1


def test_multiple_probes():
    stdout = (
        "PASS api (http://api.sandbox-foo.localhost) http=200\n"
        "PASS web (http://sandbox-foo.localhost) http=200\n"
        "PASS supervisor (http://supervisor.sandbox-foo.localhost) http=200\n"
        "healthcheck: 3 passed, 0 failed\n"
    )
    result = _parse(stdout)
    assert len(result["probes"]) == 3
    assert all(p["result"] == "pass" for p in result["probes"])
    assert result["passed"] == 3
    assert result["failed"] == 0


def test_empty_stdout_returns_empty_probes():
    result = _parse("")
    assert result["probes"] == []
    assert result["passed"] == 0
    assert result["failed"] == 0


def test_unknown_lines_are_ignored():
    stdout = "some random log line\nPASS api (http://api.x.localhost) http=200\nanother line\n"
    result = _parse(stdout)
    assert len(result["probes"]) == 1
    assert result["probes"][0]["name"] == "api"


def test_stderr_captured():
    result = _parse("", stderr="curl: (6) Could not resolve host\n", exit_code=1)
    assert "Could not resolve host" in result["raw_stderr"]
    assert result["exit_code"] == 1


def test_no_http_code_in_probe():
    stdout = "FAIL api (http://api.sandbox-foo.localhost)\n"
    result = _parse(stdout)
    assert result["probes"][0]["http_code"] is None
