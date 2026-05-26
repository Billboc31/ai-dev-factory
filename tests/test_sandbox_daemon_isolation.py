"""Tests for sandbox daemon isolation.

Verifies that each sandbox runs its own supervisor/daemon instance with an
isolated runtime root, and that cleanup never touches the main daemon.
"""

from __future__ import annotations

import json
import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.sandbox import SandboxStatus
from services.control_api.services.sandbox_manager import SandboxManager


def _ok_compose(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "done"
    m.stderr = ""
    return m


@pytest.fixture()
def mgr(tmp_path):
    return SandboxManager(sandboxes_dir=tmp_path / "sandboxes")


def _fake_popen(pid: int = 12345):
    proc = MagicMock()
    proc.pid = pid
    return proc


# ── 1. Isolated daemon startup ────────────────────────────────────────────────


def test_isolated_daemon_startup(mgr):
    """start() launches a supervisor subprocess on the sandbox's own port with
    its own isolated runtime root, and stores the PID in state."""
    s = mgr.create("T001", "/project")

    mock_proc = _fake_popen(pid=12345)
    with patch("services.control_api.services.sandbox_manager.subprocess.Popen", return_value=mock_proc) as mock_popen, \
         patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        state = mgr.start(s.id)

    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert str(state.supervisor_port) in cmd
    assert state.supervisor_port == 8090 + state.slot

    assert state.supervisor_pid == 12345

    pid_file = Path(state.sandbox_runtime_root) / "supervisor.pid"
    assert pid_file.exists()
    data = json.loads(pid_file.read_text())
    assert data["pid"] == 12345
    assert data["port"] == state.supervisor_port


# ── 2. Isolated daemon shutdown ───────────────────────────────────────────────


def test_isolated_daemon_shutdown(mgr, tmp_path):
    """stop() SIGTERMs the sandbox supervisor via the stored PID and clears
    supervisor_pid in state; a main daemon PID file elsewhere is untouched."""
    main_runtime = tmp_path / "main_runtime"
    main_runtime.mkdir()
    main_pid_file = main_runtime / "daemon.pid"
    main_pid_file.write_text(json.dumps({"pid": 99990}))

    s = mgr.create("T001", "/project")
    supervisor_pid = 55555
    state = mgr._read_state(s.id)
    state = state.model_copy(
        update={"supervisor_pid": supervisor_pid, "status": SandboxStatus.running}
    )
    mgr._write_state(state)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose), \
         patch("services.control_api.services.sandbox_manager.os.kill") as mock_kill:
        stopped = mgr.stop(s.id)

    mock_kill.assert_called_once_with(supervisor_pid, signal.SIGTERM)
    assert stopped.supervisor_pid is None

    assert main_pid_file.exists()
    assert json.loads(main_pid_file.read_text())["pid"] == 99990


# ── 3. Concurrent sandbox daemons ────────────────────────────────────────────


def test_concurrent_sandbox_daemons(mgr):
    """Two sandboxes started in sequence each get their own supervisor Popen
    call on a distinct port with a separate isolated runtime root."""
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")

    popen_calls: list[list[str]] = []
    next_pid = [10000]

    def _capture_popen(cmd, **kwargs):
        proc = MagicMock()
        proc.pid = next_pid[0]
        next_pid[0] += 1
        popen_calls.append(cmd)
        return proc

    with patch("services.control_api.services.sandbox_manager.subprocess.Popen", side_effect=_capture_popen), \
         patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        st1 = mgr.start(s1.id)
        st2 = mgr.start(s2.id)

    assert len(popen_calls) == 2
    assert st1.supervisor_port != st2.supervisor_port
    assert st1.supervisor_port != 8090
    assert st2.supervisor_port != 8090
    assert st1.sandbox_runtime_root != st2.sandbox_runtime_root
    assert st1.supervisor_pid is not None
    assert st2.supervisor_pid is not None
    assert st1.supervisor_pid != st2.supervisor_pid


# ── 4. Sandbox runtime root isolation ────────────────────────────────────────


def test_sandbox_runtime_root_isolation(mgr):
    """The sandbox .env file sets AI_DEV_FACTORY_SUPERVISOR_URL to the sandbox's
    own port and AI_DEV_FACTORY_RUNTIME_ROOT to the sandbox-scoped root, ensuring
    daemon state files land in the sandbox subtree, not the main runtime root."""
    s = mgr.create("T001", "/project")
    env_content = Path(s.env_file).read_text()

    assert (
        f"AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{s.supervisor_port}"
        in env_content
    )
    assert f"AI_DEV_FACTORY_RUNTIME_ROOT={s.sandbox_runtime_root}" in env_content
    assert s.id in s.sandbox_runtime_root

    s2 = mgr.create("T002", "/project")
    assert s.sandbox_runtime_root != s2.sandbox_runtime_root


# ── 5. Cleanup safety ─────────────────────────────────────────────────────────


def test_cleanup_safety(mgr, tmp_path):
    """destroy() SIGTERMs the sandbox supervisor and removes the sandbox
    directory without modifying a co-running main daemon's PID file."""
    main_runtime = tmp_path / "main_runtime"
    main_runtime.mkdir()
    main_pid_file = main_runtime / "daemon.pid"
    main_pid_file.write_text(json.dumps({"pid": 99991}))

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")

        runtime_root = Path(s.sandbox_runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=True)
        fake_pid = 77777
        (runtime_root / "supervisor.pid").write_text(
            json.dumps({"pid": fake_pid, "port": s.supervisor_port})
        )

        with patch("services.control_api.services.sandbox_manager.os.kill") as mock_kill:
            mgr.destroy(s.id)

        mock_kill.assert_called_once_with(fake_pid, signal.SIGTERM)

    assert not (mgr.sandboxes_dir / s.id).exists()
    assert main_pid_file.exists()
    assert json.loads(main_pid_file.read_text())["pid"] == 99991
