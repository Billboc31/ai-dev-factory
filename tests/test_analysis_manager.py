"""Tests for analysis_manager — HTTP proxy from control API to supervisor."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services import analysis_manager  # noqa: E402

_SUP = "http://localhost:8090"


class _MockResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def test_start_analysis_delegates_to_supervisor(monkeypatch):
    calls = []

    def mock_post(url, **kwargs):
        calls.append(url)
        return _MockResponse(200, {"ok": True})

    monkeypatch.setattr(analysis_manager.httpx, "post", mock_post)

    result = analysis_manager.start_analysis("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is True
    assert any("/analysis/start" in u for u in calls)


def test_start_analysis_supervisor_unreachable(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(analysis_manager.httpx, "post", mock_post)

    result = analysis_manager.start_analysis("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is False
    assert result.error == "supervisor_unreachable"


def test_start_analysis_returns_409_when_locked(monkeypatch):
    monkeypatch.setattr(
        analysis_manager.httpx,
        "post",
        lambda *a, **kw: _MockResponse(409, {"error": "locked"}),
    )

    result = analysis_manager.start_analysis("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is False
    assert result.error == "locked"


def test_start_analysis_no_supervisor_url():
    result = analysis_manager.start_analysis("proj1", "/path/proj", "claude", None)

    assert result.ok is False
    assert result.error == "no_supervisor_url"


def test_get_status_proxies_supervisor_response(monkeypatch):
    payload = {
        "state": "running",
        "started_at": "2025-01-01T00:00:00",
        "finished_at": None,
        "error": None,
        "branch": None,
        "pr_url": None,
    }

    monkeypatch.setattr(
        analysis_manager.httpx,
        "get",
        lambda *a, **kw: _MockResponse(200, payload),
    )

    status = analysis_manager.get_analysis_status("proj1", _SUP)

    assert status.state == "running"
    assert status.started_at == "2025-01-01T00:00:00"
    assert status.branch is None
