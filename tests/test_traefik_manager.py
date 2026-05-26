"""Unit tests for the global Traefik auto-start manager."""
from __future__ import annotations

import json
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

_INFRA_CID = "infra-traefik-cid-abc"
_HOST_ROUTES = "/tmp/host-runtime/proxy/routes"


def _make_inspect(
    *,
    cid: str = _INFRA_CID,
    project: str = INFRA_PROJECT_NAME,
    service: str = "traefik",
    name: str = f"/{INFRA_PROJECT_NAME}-traefik-1",
    running: bool = True,
    publish_host_80: bool = True,
    routes_source: str = _HOST_ROUTES,
) -> dict:
    ports: dict | None
    if publish_host_80:
        ports = {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "80"}]}
    else:
        ports = {"80/tcp": None}

    mounts = []
    if routes_source is not None:
        mounts.append({
            "Destination": "/routes",
            "Source": routes_source,
            "Type": "bind",
        })

    return {
        "Id": cid,
        "Name": name,
        "State": {"Status": "running" if running else "exited", "Running": running},
        "Config": {
            "Labels": {
                "com.docker.compose.project": project,
                "com.docker.compose.service": service,
            }
        },
        "NetworkSettings": {"Ports": ports},
        "Mounts": mounts,
    }


class _SockFactory:
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
    """Script docker compose ps / inspect / ps based on command shape."""

    def __init__(
        self,
        *,
        infra_cid: str | None = _INFRA_CID,
        inspect: dict | None = None,
        ps_owner_line: str | None = "ai-dev-factory-traefik-1\t0.0.0.0:80->80/tcp",
        responses: list[tuple[int, str, str]] | None = None,
    ):
        self.infra_cid = infra_cid
        self.inspect_data = inspect if inspect is not None else _make_inspect()
        self.ps_owner_line = ps_owner_line
        self.responses = list(responses or [])
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[0:2] == ["docker", "compose"] and "ps" in cmd:
            out = f"{self.infra_cid}\n" if self.infra_cid else ""
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=out, stderr="")
        if cmd[0:2] == ["docker", "inspect"]:
            payload = json.dumps([self.inspect_data])
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=payload, stderr="")
        if cmd[0:2] == ["docker", "ps"] and "--format" in cmd:
            out = self.ps_owner_line or ""
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=out, stderr="")
        if cmd[0] == "bash":
            if self.responses:
                rc, stdout, stderr = self.responses.pop(0)
            else:
                rc, stdout, stderr = 0, "", ""
            return subprocess.CompletedProcess(args=cmd, returncode=rc, stdout=stdout, stderr=stderr)
        if cmd[0:2] == ["docker", "compose"] and "down" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if self.responses:
            rc, stdout, stderr = self.responses[0]
            if len(self.responses) > 1:
                self.responses.pop(0)
        else:
            rc, stdout, stderr = 0, "", ""
        return subprocess.CompletedProcess(args=cmd, returncode=rc, stdout=stdout, stderr=stderr)


def _mk_mgr(*, listening, runner=None, sleeper=None):
    sock = _SockFactory(listening=listening)
    runner = runner or _Runner()
    mgr = TraefikManager(
        socket_factory=sock,
        runner=runner,
        sleeper=sleeper or (lambda _s: None),
    )
    return mgr, sock, runner


# ── Static helpers ────────────────────────────────────────────────────────────


def test_publishes_host_port_true_when_bound():
    assert TraefikManager.publishes_host_port(_make_inspect(publish_host_80=True))


def test_publishes_host_port_false_when_internal_only():
    assert not TraefikManager.publishes_host_port(_make_inspect(publish_host_80=False))


def test_compose_labels_match_infra_project():
    assert TraefikManager.compose_labels_match(_make_inspect())


def test_compose_labels_reject_wrong_project():
    assert not TraefikManager.compose_labels_match(
        _make_inspect(project="ai-dev-factory")
    )


# ── _ready / infra_owns_host_port ─────────────────────────────────────────────


def test_ready_false_when_infra_running_but_not_publishing_host_80(monkeypatch, tmp_path):
    """Regression: infra Up with 80/tcp only; old traefik owns 0.0.0.0:80."""
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    inspect = _make_inspect(publish_host_80=False, routes_source=str(host_routes))
    mgr, _, _ = _mk_mgr(
        listening=True,
        runner=_Runner(inspect=inspect, ps_owner_line="ai-dev-factory-traefik-1\t0.0.0.0:80->80/tcp"),
    )
    assert mgr.is_running() is True
    assert mgr.infra_owns_host_port() is False
    assert mgr._ready() is False


def test_ready_false_when_old_traefik_owns_port_and_infra_running_internally(
    monkeypatch, tmp_path,
):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    mgr, _, _ = _mk_mgr(
        listening=True,
        runner=_Runner(
            inspect=_make_inspect(publish_host_80=False, routes_source=str(host_routes)),
            ps_owner_line="ai-dev-factory-traefik-1\t0.0.0.0:80->80/tcp",
        ),
    )
    assert mgr.ensure_running(timeout=0.05) is False


def test_ready_true_when_infra_publishes_host_80(monkeypatch, tmp_path):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    mgr, _, runner = _mk_mgr(
        listening=True,
        runner=_Runner(
            inspect=_make_inspect(publish_host_80=True, routes_source=str(host_routes)),
        ),
    )
    assert mgr._ready() is True
    assert mgr.ensure_running() is True
    assert all(c[0] != "bash" for c in runner.calls)


def test_ready_false_when_routes_mount_mismatch(monkeypatch, tmp_path):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    mgr, _, _ = _mk_mgr(
        listening=True,
        runner=_Runner(
            inspect=_make_inspect(
                publish_host_80=True,
                routes_source="/wrong/proxy/routes",
            ),
        ),
    )
    assert mgr._ready() is False


def test_ensure_running_logs_remediation_when_port_owned_by_other(caplog, monkeypatch, tmp_path):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    runner = _Runner(
        inspect=_make_inspect(publish_host_80=False, routes_source=str(host_routes)),
        ps_owner_line="ai-dev-factory-traefik-1\t0.0.0.0:80->80/tcp",
        responses=[
            (1, "", "Bind for 0.0.0.0:80 failed: port is already allocated"),
        ],
    )
    mgr, _, _ = _mk_mgr(listening=True, runner=runner)
    assert mgr.ensure_running(timeout=0.05) is False

    combined = caplog.text
    assert "port 80 is owned by another container" in combined
    assert "ai-dev-factory-infra" in combined
    assert "ai-dev-factory-traefik-1" in combined
    assert "docker stop ai-dev-factory-traefik-1" in combined
    assert "start_traefik.sh up" in combined


def test_ensure_running_restarts_infra_when_running_without_host_bind(monkeypatch, tmp_path):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    good_inspect = _make_inspect(publish_host_80=True, routes_source=str(host_routes))
    bad_inspect = _make_inspect(publish_host_80=False, routes_source=str(host_routes))

    class _RestartRunner(_Runner):
        def __init__(self):
            super().__init__(inspect=bad_inspect)
            self._inspect = bad_inspect
            self._n = 0

        def __call__(self, cmd, **kwargs):
            if cmd[0:2] == ["docker", "inspect"]:
                self._n += 1
                data = good_inspect if self._n > 2 else bad_inspect
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout=json.dumps([data]), stderr=""
                )
            if cmd[0] == "bash":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            return super().__call__(cmd, **kwargs)

    sock = _SockFactory(listening=True)

    def flip(_s):
        pass

    restart_runner = _RestartRunner()
    mgr = TraefikManager(socket_factory=sock, runner=restart_runner, sleeper=flip)
    assert mgr.ensure_running(timeout=1.0) is True
    assert any("down" in c for c in restart_runner.calls)


# ── Legacy probes ─────────────────────────────────────────────────────────────


def test_is_listening_returns_true_on_open_port():
    mgr, _, _ = _mk_mgr(listening=True)
    assert mgr.is_listening() is True


def test_is_running_returns_false_when_no_container():
    mgr, _, _ = _mk_mgr(listening=False, runner=_Runner(infra_cid=None))
    assert mgr.is_running() is False


def test_ensure_running_calls_start_script_when_not_listening(monkeypatch, tmp_path):
    host_routes = tmp_path / "host" / "proxy" / "routes"
    host_routes.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host"))

    sock = _SockFactory(listening=False)
    good = _make_inspect(publish_host_80=True, routes_source=str(host_routes))

    class _BootRunner(_Runner):
        def __call__(self, cmd, **kwargs):
            if cmd[0:2] == ["docker", "inspect"]:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout=json.dumps([good]), stderr=""
                )
            return super().__call__(cmd, **kwargs)

    def flip(_s):
        sock.listening = True

    mgr = TraefikManager(socket_factory=sock, runner=_BootRunner(), sleeper=flip)
    assert mgr.ensure_running() is True


def test_module_level_ensure_running_returns_bool(monkeypatch):
    class _Stub:
        def ensure_running(self, timeout: float = 15.0) -> bool:
            return True

    import services.control_api.services.traefik_manager as m

    monkeypatch.setattr(m, "TraefikManager", lambda: _Stub())
    assert module_ensure_running() is True


def test_infra_project_name_matches_start_script():
    repo = Path(__file__).resolve().parents[1]
    script = (repo / "deploy" / "infra" / "start_traefik.sh").read_text()
    assert INFRA_PROJECT_NAME in script
