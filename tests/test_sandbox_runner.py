"""Tests for the sandbox HTTP-client manager.

``services/control_api/services/sandbox_runner.py`` is now a pure
HTTP client that proxies requests to the host-side supervisor. These
tests cover the proxy logic (URL resolution, error mapping, payload
shape) without touching the network or the worker process — that's
the job of ``test_run_sandbox_worker.py`` and
``test_supervisor_sandbox.py``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.schemas import SandboxValidationState  # noqa: E402
from services.control_api.services import sandbox_runner  # noqa: E402


# ── Fake httpx ────────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        return self._payload


class _FakeHttpx:
    def __init__(self):
        self.posts: list[tuple[str, dict, float]] = []
        self.gets: list[tuple[str, dict, float]] = []
        self.next_post: _FakeResponse | None = None
        self.next_get: _FakeResponse | None = None
        self.raise_connect_error_on_post = False
        self.raise_connect_error_on_get = False

    def post(self, url: str, json=None, timeout=None):
        if self.raise_connect_error_on_post:
            import httpx
            raise httpx.ConnectError("boom")
        self.posts.append((url, json or {}, timeout))
        return self.next_post or _FakeResponse({"ok": True})

    def get(self, url: str, params=None, timeout=None):
        if self.raise_connect_error_on_get:
            import httpx
            raise httpx.ConnectError("boom")
        self.gets.append((url, params or {}, timeout))
        return self.next_get or _FakeResponse({"state": "idle"})


@pytest.fixture
def fake_httpx(monkeypatch):
    fake = _FakeHttpx()
    monkeypatch.setattr(sandbox_runner, "httpx", _StubHttpxModule(fake))
    return fake


class _StubHttpxModule:
    """Mimic the few attributes our manager touches on the real httpx
    module (post, get, ConnectError)."""

    def __init__(self, fake: _FakeHttpx):
        self._fake = fake
        import httpx as _real
        self.ConnectError = _real.ConnectError

    def post(self, *args, **kwargs):
        return self._fake.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._fake.get(*args, **kwargs)


# ── start_sandbox_validation ──────────────────────────────────────────────────


def test_start_requires_supervisor_url(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    result = sandbox_runner.start_sandbox_validation("p1", "/host/p1", None)
    assert result.ok is False
    assert result.error == "no_supervisor_url"


def test_start_picks_up_env_supervisor_url(monkeypatch, fake_httpx):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://supervisor:9000/")
    result = sandbox_runner.start_sandbox_validation("p1", "/host/p1")
    assert result.ok is True
    assert len(fake_httpx.posts) == 1
    url, body, _ = fake_httpx.posts[0]
    # trailing slash must be stripped before joining the path
    assert url == "http://supervisor:9000/sandbox/start"
    assert body == {"project_root": "/host/p1", "project_id": "p1", "mode": "validation"}


def test_start_propagates_409_as_locked(fake_httpx):
    fake_httpx.next_post = _FakeResponse(
        {"ok": False, "error": "locked"}, status_code=409
    )
    result = sandbox_runner.start_sandbox_validation(
        "p1", "/host/p1", "http://supervisor:9000"
    )
    assert result.ok is False
    assert result.error == "locked"


def test_start_maps_connect_error(fake_httpx):
    fake_httpx.raise_connect_error_on_post = True
    result = sandbox_runner.start_sandbox_validation(
        "p1", "/host/p1", "http://supervisor:9000"
    )
    assert result.ok is False
    assert result.error == "supervisor_unreachable"


def test_start_passes_container_side_root_unchanged(fake_httpx):
    """The supervisor is responsible for container→host mapping. The
    manager must not mutate ``project_root`` — that would double-map."""
    sandbox_runner.start_sandbox_validation(
        "p1", "/app", "http://supervisor:9000"
    )
    body = fake_httpx.posts[0][1]
    assert body["project_root"] == "/app"


# ── get_sandbox_state ─────────────────────────────────────────────────────────


def test_state_returns_idle_without_supervisor(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    state = sandbox_runner.get_sandbox_state("p1", None)
    assert isinstance(state, SandboxValidationState)
    assert state.state == "idle"


def test_state_decodes_steps_from_payload(fake_httpx):
    fake_httpx.next_get = _FakeResponse({
        "state": "running",
        "sandbox_id": "p1-20260519T140000",
        "started_at": "2026-05-19T14:00:00",
        "finished_at": None,
        "error": None,
        "last_step": "build.sh",
        "steps": [
            {"name": "bootstrap.sh", "status": "success", "exit_code": 0},
            {"name": "build.sh", "status": "failed", "exit_code": 1},
        ],
    })

    state = sandbox_runner.get_sandbox_state("p1", "http://supervisor:9000")
    assert state.state == "running"
    assert state.sandbox_id == "p1-20260519T140000"
    assert len(state.steps) == 2
    assert state.steps[0].name == "bootstrap.sh"
    assert state.steps[1].status == "failed"


def test_state_connect_error_yields_failed(fake_httpx):
    fake_httpx.raise_connect_error_on_get = True
    state = sandbox_runner.get_sandbox_state("p1", "http://supervisor:9000")
    assert state.state == "failed"
    assert state.error == "supervisor_unreachable"


def test_state_malformed_payload_falls_back_to_idle(fake_httpx, monkeypatch):
    """If the supervisor sends garbage we must NOT crash the API — return
    an idle state and let the dashboard recover on the next poll."""
    class _Broken:
        status_code = 500

        def json(self):
            raise json.JSONDecodeError("boom", "x", 0)

    fake_httpx.next_get = _Broken()
    state = sandbox_runner.get_sandbox_state("p1", "http://supervisor:9000")
    assert state.state == "idle"


# ── get_sandbox_logs ──────────────────────────────────────────────────────────


def test_logs_empty_without_supervisor(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    assert sandbox_runner.get_sandbox_logs("p1", None) == []


def test_logs_returns_lines_from_supervisor(fake_httpx):
    fake_httpx.next_get = _FakeResponse({"lines": ["a", "b", "c"]})
    out = sandbox_runner.get_sandbox_logs("p1", "http://supervisor:9000", lines=50)
    assert out == ["a", "b", "c"]
    url, params, _ = fake_httpx.gets[0]
    assert url == "http://supervisor:9000/sandbox/p1/logs"
    assert params == {"lines": 50}


def test_logs_swallows_errors(fake_httpx):
    fake_httpx.raise_connect_error_on_get = True
    # ConnectError → returned via generic except. Must yield empty list,
    # never propagate.
    assert sandbox_runner.get_sandbox_logs("p1", "http://supervisor:9000") == []
