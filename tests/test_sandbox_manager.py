"""Unit tests for SandboxManager — subprocess calls are mocked, no Docker required."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.sandbox import SandboxStatus
from services.control_api.services.sandbox_manager import SandboxManager, SandboxNotFoundError


def _ok_compose(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "done"
    m.stderr = ""
    return m


def _fail_compose(*args, **kwargs):
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "error"
    return m


@pytest.fixture()
def mgr(tmp_path):
    m = SandboxManager(sandboxes_dir=tmp_path / "sandboxes")
    # Disable Traefik auto-start so the tests don't try to talk to
    # docker. The auto-start path is covered by
    # ``test_traefik_manager.py`` and ``test_proxy_manager.py``.
    m._proxy._auto_ensure_infra = False
    return m


def test_create_allocates_unique_ports(mgr):
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")
    assert s1.slot != s2.slot
    assert s1.ports["web"] != s2.ports["web"]
    assert s1.ports["api"] != s2.ports["api"]


def test_create_does_not_conflict_with_main_runtime(mgr):
    s = mgr.create("T001", "/project")
    assert s.slot >= 1
    assert s.ports["web"] != 3000
    assert s.ports["api"] != 8080


def test_port_registry_released_on_destroy(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")
        slot_before = s.slot
        mgr.destroy(s.id)
        s2 = mgr.create("T002", "/project")
        assert s2.slot == slot_before


def test_state_written_on_create(mgr):
    s = mgr.create("T001", "/project")
    state_file = mgr.sandboxes_dir / s.id / "state.json"
    assert state_file.exists()
    loaded = mgr.status(s.id)
    assert loaded.id == s.id
    assert loaded.ticket_id == "T001"


def test_compose_project_name_is_compose_valid(mgr):
    """Even though SandboxManager mints uuid-hex IDs that are already
    Compose-valid, run the produced name through Compose's regex so a
    future change to the ID format doesn't silently regress this."""
    import re
    s = mgr.create("T001", "/project")
    assert re.match(r"^[a-z0-9][a-z0-9_-]*$", s.compose_project), (
        f"compose_project {s.compose_project!r} is not Compose-valid"
    )


def test_env_file_written_on_create(mgr):
    s = mgr.create("T001", "/project")
    env_file = Path(s.env_file)
    assert env_file.exists()
    content = env_file.read_text()
    assert f"WEB_PORT={s.ports['web']}" in content
    assert f"API_PORT={s.ports['api']}" in content
    assert f"COMPOSE_PROJECT_NAME={s.compose_project}" in content


def test_env_file_contains_pretty_urls_and_supervisor_split(mgr):
    """Operational scripts (start.sh / healthcheck.sh) read these env
    vars to probe the reverse-proxy URLs instead of direct ports, and
    to use the loopback supervisor URL from host shells (the docker-
    internal URL is unresolvable there)."""
    s = mgr.create("T001", "/project")
    content = Path(s.env_file).read_text()
    # Pretty URLs deterministic from sandbox id.
    assert f"SANDBOX_ID={s.id}" in content
    assert f"SANDBOX_WEB_URL=http://sandbox-{s.id}.ai-dev-factory.localhost" in content
    assert f"SANDBOX_API_URL=http://api.sandbox-{s.id}.ai-dev-factory.localhost" in content
    # Two distinct supervisor URLs.
    assert f"AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{s.supervisor_port}" in content
    assert f"AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL=http://127.0.0.1:{s.supervisor_port}" in content


def test_cleanup_stale_routes_removes_orphans(mgr, tmp_path, monkeypatch):
    """A sandbox that died without an unregister step leaves a stale
    route file. ``cleanup_stale_routes`` reaps those without touching
    routes whose sandbox still exists or the infra-owned dashboard."""
    # Point the proxy routes dir to a tmp location and disable the
    # Traefik auto-start path (we're not testing docker here).
    routes_dir = tmp_path / "routes"
    mgr._proxy.routes_dir = routes_dir
    mgr._proxy.routes_dir.mkdir(parents=True, exist_ok=True)
    mgr._proxy._auto_ensure_infra = False
    (routes_dir / "_dashboard.yml").write_text("infra", encoding="utf-8")

    # One live sandbox + two orphan route files.
    live = mgr.create("T001", "/project")
    mgr._proxy.register(live.id, live.ports)
    (routes_dir / "ghost-aaa.yml").write_text("dummy", encoding="utf-8")
    (routes_dir / "ghost-bbb.yml").write_text("dummy", encoding="utf-8")

    removed = mgr.cleanup_stale_routes()
    assert sorted(removed) == ["ghost-aaa", "ghost-bbb"]
    assert (routes_dir / f"{live.id}.yml").exists()
    assert (routes_dir / "_dashboard.yml").exists()


def test_lifecycle_transitions(mgr):
    s = mgr.create("T001", "/project")
    assert s.status == SandboxStatus.stopped

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.start(s.id)
        assert s.status == SandboxStatus.running

        s = mgr.stop(s.id)
        assert s.status == SandboxStatus.stopped


def test_start_failure_sets_error_status(mgr):
    s = mgr.create("T001", "/project")
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_fail_compose):
        s = mgr.start(s.id)
        assert s.status == SandboxStatus.error


def test_list_returns_all_sandboxes(mgr):
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")
    all_ids = {s.id for s in mgr.list()}
    assert s1.id in all_ids
    assert s2.id in all_ids


def test_destroy_removes_sandbox_directory(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")
        sandbox_dir = mgr.sandboxes_dir / s.id
        assert sandbox_dir.exists()
        mgr.destroy(s.id)
        assert not sandbox_dir.exists()


def test_status_raises_for_unknown_sandbox(mgr):
    with pytest.raises(SandboxNotFoundError):
        mgr.status("nonexistent")


def test_cleanup_old_removes_stale_sandboxes(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")
        # Backdate the created_at timestamp to 10 days ago
        state = mgr.status(s.id)
        old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
        mgr._write_state(state.model_copy(update={"created_at": old_ts}))

        destroyed = mgr.cleanup_old(max_age_days=7)
        assert destroyed == 1
        assert not (mgr.sandboxes_dir / s.id).exists()


def test_cleanup_old_keeps_recent_sandboxes(mgr):
    s = mgr.create("T001", "/project")
    destroyed = mgr.cleanup_old(max_age_days=7)
    assert destroyed == 0
    assert (mgr.sandboxes_dir / s.id).exists()


def test_logs_calls_docker_compose(mgr):
    s = mgr.create("T001", "/project")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "log output line\n"
    mock_result.stderr = ""
    with patch("services.control_api.services.sandbox_manager.subprocess.run", return_value=mock_result) as mock_run:
        output = mgr.logs(s.id)
    assert output == "log output line\n"
    cmd = mock_run.call_args[0][0]
    assert "logs" in cmd
    assert s.compose_project in cmd


def test_stop_calls_terminate_supervisor(mgr):
    s = mgr.create("T001", "/project")
    runtime_root = Path(s.sandbox_runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    pid_path = runtime_root / "supervisor.pid"
    import os
    pid_path.write_text(f'{{"pid": {os.getpid()}}}', encoding="utf-8")

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        with patch("services.control_api.services.sandbox_manager.os.kill") as mock_kill:
            mgr.stop(s.id)
    mock_kill.assert_called_once()
    args = mock_kill.call_args[0]
    assert args[0] == os.getpid()


def test_stop_cleans_pid_and_lock_files(mgr):
    s = mgr.create("T001", "/project")
    runtime_root = Path(s.sandbox_runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    pid_file = runtime_root / "worker.pid"
    lock_file = runtime_root / "run.lock"
    pid_file.write_text('{"pid": 99999}', encoding="utf-8")
    lock_file.write_text('{"pid": 99999}', encoding="utf-8")

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        mgr.stop(s.id)

    assert not pid_file.exists()
    assert not lock_file.exists()


def test_stop_retains_port_slot(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")
        slot_before = s.slot
        mgr.start(s.id)
        mgr.stop(s.id)
        registry = mgr._read_registry()
        assert s.id in registry
        assert registry[s.id] == slot_before


def test_restart_transitions_running(mgr):
    s = mgr.create("T001", "/project")
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.start(s.id)
        assert s.status == SandboxStatus.running
        s = mgr.restart(s.id)
        assert s.status == SandboxStatus.running


def test_refresh_returns_state_no_subprocess(mgr):
    s = mgr.create("T001", "/project")
    with patch("services.control_api.services.sandbox_manager.subprocess.run") as mock_run:
        result = mgr.refresh(s.id)
    mock_run.assert_not_called()
    assert result.id == s.id
    assert result.status == SandboxStatus.stopped


# ── T148: undeploy lifecycle tests ───────────────────────────────────────────


def test_compose_project_stopped_on_destroy(mgr):
    """docker compose down is called with the correct project before sandbox files are removed."""
    s = mgr.create("T001", "/project")
    compose_down_calls: list[str] = []

    def capture_run(cmd, *args, **kwargs):
        if isinstance(cmd, str) and "docker compose" in cmd:
            compose_down_calls.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    sandbox_dir = mgr.sandboxes_dir / s.id

    # Both sandbox_manager and undeploy_runner use the same subprocess module —
    # a single patch on the shared target is sufficient.
    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=capture_run,
    ):
        mgr.destroy(s.id)

    assert not sandbox_dir.exists(), "sandbox dir must be removed after destroy"
    assert compose_down_calls, "docker compose down must have been called"
    assert s.compose_project in compose_down_calls[0]


def test_runtime_process_terminated_before_file_removal(mgr):
    """Supervisor SIGTERM must occur before sandbox directory removal."""
    s = mgr.create("T001", "/project")
    runtime_root = Path(s.sandbox_runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)

    # Use a PID that cannot exist (> max PID on Linux/macOS) so os.kill would
    # normally raise; mocking it lets us record the call order safely.
    fake_pid = 9_999_999
    pid_path = runtime_root / "supervisor.pid"
    pid_path.write_text(f'{{"pid": {fake_pid}}}', encoding="utf-8")

    order: list[str] = []

    def record_kill(pid, sig):
        order.append("kill")

    real_rmtree = shutil.rmtree

    def record_rmtree(path, *a, **kw):
        order.append("rmtree")
        real_rmtree(path, *a, **kw)

    with patch("services.control_api.services.sandbox_manager.os.kill", side_effect=record_kill):
        with patch("services.control_api.services.sandbox_manager.shutil.rmtree", side_effect=record_rmtree):
            with patch("services.control_api.services.undeploy_runner.subprocess.run", side_effect=_ok_compose):
                mgr.destroy(s.id)

    assert "kill" in order, "SIGTERM was never sent"
    assert "rmtree" in order, "rmtree was never called"
    assert order.index("kill") < order.index("rmtree"), "SIGTERM must happen before rmtree"


def test_worktree_removed_after_undeploy(mgr):
    """git worktree remove is called after undeploy, and the sandbox dir is gone."""
    s = mgr.create("T001", "/project")
    worktree_calls: list[list[str]] = []

    def capture_subprocess(cmd, *args, **kwargs):
        if isinstance(cmd, list) and "worktree" in cmd:
            worktree_calls.append(cmd)
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    # Patch a worktree_path into the state so destroy tries to remove it.
    state = mgr.status(s.id)
    mgr._write_state(state.model_copy(update={"worktree_path": "/tmp/fake_worktree"}))

    with patch("services.control_api.services.undeploy_runner.subprocess.run", side_effect=_ok_compose):
        with patch(
            "services.control_api.services.sandbox_manager.subprocess.run",
            side_effect=capture_subprocess,
        ):
            mgr.destroy(s.id)

    assert not (mgr.sandboxes_dir / s.id).exists()
    assert any("worktree" in cmd for cmd in worktree_calls), "worktree remove must be called"


def test_cleanup_idempotency(mgr):
    """Calling destroy twice on the same sandbox must not raise."""
    with patch("services.control_api.services.undeploy_runner.subprocess.run", side_effect=_ok_compose):
        with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
            s = mgr.create("T001", "/project")
            mgr.destroy(s.id)
            mgr.destroy(s.id)  # second call must be a no-op


def test_recreate_sandbox_after_cleanup(mgr):
    """Creating a new sandbox after destroying a prior one must succeed without 'already running'."""
    with patch("services.control_api.services.undeploy_runner.subprocess.run", side_effect=_ok_compose):
        with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
            s1 = mgr.create("T001", "/project")
            mgr.destroy(s1.id)

    s2 = mgr.create("T001", "/project")
    assert s2.id != s1.id
    assert s2.status == SandboxStatus.stopped
