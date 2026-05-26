"""Unit tests for the global Traefik auto-start manager.

The TraefikManager talks to docker and the TCP stack — we stub both
so this suite stays hermetic and fast. The stubs follow the standard
``subprocess.CompletedProcess`` shape so we can exercise the same
branches the real ``subprocess.run`` would trigger.
"""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.traefik_manager import (  # noqa: E402
    INFRA_PROJECT_NAME,
    TraefikManager,
    ensure_running as module_ensure_running,
)


# ── Test doubles ──────────────────────────────────────────────────────────────


class _SockFactory:
    """Stub for ``socket.create_connection``. Drive ``listening`` to
    flip the manager between "already up" and "not up" states."""

    def __init__(self, listening: bool = False):
        self.listening = listening
        self.calls: list[tuple] = []

    def __call__(self, address, timeout):
        self.calls.append((address, timeout))
        if self.listening:
            return _DummySocket()
        raise ConnectionRefusedError(f"stub: {address!r} closed")


class _DummySocket:
    def close(self) -> None:
        pass


class _Runner:
    """Stub for ``subprocess.run``. Each call pops a scripted response
    off ``responses``; if the script is shorter than the call count
    the last response is returned (so a single ``rc=0`` covers all
    follow-up invocations without test-fixture bookkeeping)."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if self.responses:
            entry = self.responses[0]
            if len(self.responses) > 1:
                self.responses.pop(0)
            rc, stdout, stderr = entry
        else:
            rc, stdout, stderr = 0, "", ""
        return subprocess.CompletedProcess(
            args=cmd, returncode=rc, stdout=stdout, stderr=stderr,
        )


def _mk_mgr(*, listening, responses=None, sleeper=None):
    sock = _SockFactory(listening=listening)
    runner = _Runner(responses=responses)
    mgr = TraefikManager(
        socket_factory=sock,
        runner=runner,
        sleeper=sleeper or (lambda _s: None),
    )
    return mgr, sock, runner


# ── Probes ────────────────────────────────────────────────────────────────────


def test_is_listening_returns_true_on_open_port():
    mgr, _, _ = _mk_mgr(listening=True)
    assert mgr.is_listening() is True


def test_is_listening_returns_false_on_refused_connection():
    mgr, _, _ = _mk_mgr(listening=False)
    assert mgr.is_listening() is False


def test_is_running_returns_true_when_compose_lists_container():
    mgr, _, runner = _mk_mgr(
        listening=False,
        responses=[(0, "container-id-123\n", "")],
    )
    assert mgr.is_running() is True
    cmd = runner.calls[0]
    assert cmd[:2] == ["docker", "compose"]
    assert "-p" in cmd and INFRA_PROJECT_NAME in cmd
    assert "ps" in cmd and "traefik" in cmd


def test_is_running_returns_false_when_compose_returns_empty():
    mgr, _, _ = _mk_mgr(
        listening=False,
        responses=[(0, "", "")],
    )
    assert mgr.is_running() is False


def test_is_running_returns_false_when_docker_missing():
    """Docker not installed → ``FileNotFoundError`` from ``subprocess.run``."""
    def boom(*a, **k):
        raise FileNotFoundError("docker")
    mgr = TraefikManager(socket_factory=_SockFactory(False), runner=boom)
    assert mgr.is_running() is False


# ── ensure_running ───────────────────────────────────────────────────────────


def test_ensure_running_noop_when_already_listening():
    mgr, sock, runner = _mk_mgr(listening=True)
    assert mgr.ensure_running() is True
    assert runner.calls == [], "must not exec docker if already up"
    assert sock.calls, "must probe TCP at least once"


def test_ensure_running_calls_start_script_when_not_listening():
    """Not listening before, listening after the script — happy path."""
    sock = _SockFactory(listening=False)
    runner = _Runner(responses=[(0, "", "")])
    mgr = TraefikManager(
        socket_factory=sock, runner=runner,
        sleeper=lambda _s: setattr(sock, "listening", True),
    )
    assert mgr.ensure_running() is True
    # First call is `bash deploy/infra/start_traefik.sh up`.
    assert runner.calls[0][0] == "bash"
    assert runner.calls[0][-1] == "up"
    assert "start_traefik.sh" in runner.calls[0][1]


def test_ensure_running_recovers_from_missing_network():
    """The classic docker failure ``network not found`` triggers a
    ``compose down --remove-orphans`` followed by a retry."""
    sock = _SockFactory(listening=False)
    runner = _Runner(responses=[
        (1, "", "Error: network 7fa3 not found"),  # up #1 fails
        (0, "", ""),                                # down --remove-orphans
        (0, "", ""),                                # up #2 succeeds
    ])
    mgr = TraefikManager(
        socket_factory=sock, runner=runner,
        sleeper=lambda _s: setattr(sock, "listening", True),
    )
    assert mgr.ensure_running() is True

    assert len(runner.calls) == 3
    # 1st: up
    assert runner.calls[0][-1] == "up"
    # 2nd: down with --remove-orphans (no project / app stack touched)
    assert "down" in runner.calls[1]
    assert "--remove-orphans" in runner.calls[1]
    assert INFRA_PROJECT_NAME in runner.calls[1]
    # 3rd: retry up
    assert runner.calls[2][-1] == "up"


def test_ensure_running_returns_false_on_non_network_failure():
    """Other failures (e.g. port 80 taken) should NOT trigger the
    ``compose down`` recovery — that would mask the real cause and
    needlessly churn the infra project."""
    sock = _SockFactory(listening=False)
    runner = _Runner(responses=[
        (1, "", "Error: Bind for 0.0.0.0:80 failed: port is already allocated"),
    ])
    mgr = TraefikManager(socket_factory=sock, runner=runner)
    assert mgr.ensure_running(timeout=0.1) is False
    # Only one docker call — no recovery attempt.
    assert len(runner.calls) == 1


def test_ensure_running_returns_false_when_not_ready_before_timeout():
    sock = _SockFactory(listening=False)
    runner = _Runner(responses=[(0, "", "")])
    sleeps: list[float] = []

    mgr = TraefikManager(
        socket_factory=sock, runner=runner,
        sleeper=lambda s: sleeps.append(s),
    )
    assert mgr.ensure_running(timeout=0.05) is False


def test_ensure_running_succeeds_when_listening_returns_true_during_wait():
    sock = _SockFactory(listening=False)
    runner = _Runner(responses=[(0, "", "")])
    poll_count = {"n": 0}

    def maybe_open(_s):
        poll_count["n"] += 1
        if poll_count["n"] >= 2:
            sock.listening = True

    mgr = TraefikManager(
        socket_factory=sock, runner=runner, sleeper=maybe_open,
    )
    assert mgr.ensure_running(timeout=5.0) is True


# ── Module-level convenience ─────────────────────────────────────────────────


def test_module_level_ensure_running_returns_bool(monkeypatch):
    """The module function is just a thin façade; mock the underlying
    class to keep this hermetic."""
    class _Stub:
        def __init__(self):
            pass
        def ensure_running(self, timeout: float = 15.0) -> bool:
            return True
    import services.control_api.services.traefik_manager as m
    monkeypatch.setattr(m, "TraefikManager", lambda: _Stub())
    assert module_ensure_running() is True


# ── Compose project name invariant ────────────────────────────────────────────


def test_infra_project_name_matches_start_script():
    """Drift detection: if either side changes the project name, the
    `is_running` lookup would target the wrong project. The single
    source of truth is the module constant; the script just embeds it."""
    repo = Path(__file__).resolve().parents[1]
    script = (repo / "deploy" / "infra" / "start_traefik.sh").read_text()
    assert INFRA_PROJECT_NAME in script, (
        f"{INFRA_PROJECT_NAME!r} must appear in deploy/infra/start_traefik.sh "
        f"for TraefikManager.is_running / ensure_running to target the "
        f"same compose project the script brings up"
    )
