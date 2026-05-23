"""Unit tests for SandboxManager — subprocess calls are mocked, no Docker required."""

from __future__ import annotations

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
    return SandboxManager(sandboxes_dir=tmp_path / "sandboxes")


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
