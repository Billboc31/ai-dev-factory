"""Tests for concurrent sandbox isolation — unique ports, compose names, and cleanup."""

from __future__ import annotations

import json
import signal
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def test_concurrent_create_unique_ports(mgr):
    sandboxes = [mgr.create(f"T{i:03d}", "/project") for i in range(5)]
    web_ports = [s.ports["web"] for s in sandboxes]
    api_ports = [s.ports["api"] for s in sandboxes]
    assert len(set(web_ports)) == 5
    assert len(set(api_ports)) == 5


def test_concurrent_create_unique_compose_names(mgr):
    sandboxes = [mgr.create(f"T{i:03d}", "/project") for i in range(5)]
    names = [s.compose_project for s in sandboxes]
    assert len(set(names)) == 5


def test_concurrent_create_unique_ids(mgr):
    sandboxes = [mgr.create(f"T{i:03d}", "/project") for i in range(5)]
    ids = [s.id for s in sandboxes]
    assert len(set(ids)) == 5


def test_ports_never_collide_with_main_runtime(mgr):
    for i in range(10):
        s = mgr.create(f"T{i:03d}", "/project")
        assert s.ports["web"] != 3000, "web port must not overlap main runtime"
        assert s.ports["api"] != 8080, "api port must not overlap main runtime"


def test_cleanup_completed_destroys_completed_sandboxes(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s1 = mgr.create("T001", "/project")
        s2 = mgr.create("T002", "/project")

        # Mark s1 completed; leave s2 running.
        mgr.mark_completed(s1.id)

        destroyed = mgr.cleanup_completed(max_age_minutes=0)
        assert destroyed == 1
        assert not (mgr.sandboxes_dir / s1.id).exists()
        assert (mgr.sandboxes_dir / s2.id).exists()


def test_cleanup_completed_respects_age_threshold(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")
        mgr.mark_completed(s.id)

        # Default threshold is 30 minutes — a just-completed sandbox should NOT be destroyed.
        destroyed = mgr.cleanup_completed(max_age_minutes=30)
        assert destroyed == 0
        assert (mgr.sandboxes_dir / s.id).exists()


def test_cleanup_completed_ignores_non_completed_sandboxes(mgr):
    s = mgr.create("T001", "/project")
    destroyed = mgr.cleanup_completed(max_age_minutes=0)
    assert destroyed == 0
    assert (mgr.sandboxes_dir / s.id).exists()


def test_env_files_are_isolated(mgr):
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")
    assert s1.env_file != s2.env_file
    env1 = Path(s1.env_file).read_text()
    env2 = Path(s2.env_file).read_text()
    assert s1.compose_project in env1
    assert s2.compose_project in env2
    assert s1.compose_project not in env2
    assert s2.compose_project not in env1


# ── Isolated runtime roots ────────────────────────────────────────────────────


def test_isolated_runtime_root(mgr):
    """Each sandbox gets a distinct sandbox_runtime_root; state written in one
    is invisible from the other."""
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")

    assert s1.sandbox_runtime_root != s2.sandbox_runtime_root
    assert s1.id in s1.sandbox_runtime_root
    assert s2.id in s2.sandbox_runtime_root

    # Write a sentinel file under s1's runtime root.
    r1 = Path(s1.sandbox_runtime_root)
    r1.mkdir(parents=True, exist_ok=True)
    (r1 / "sentinel.txt").write_text("s1-only")

    # It must not appear under s2's runtime root.
    r2 = Path(s2.sandbox_runtime_root)
    r2.mkdir(parents=True, exist_ok=True)
    assert not (r2 / "sentinel.txt").exists()


# ── Isolated supervisor ports ─────────────────────────────────────────────────


def test_isolated_supervisor_port(mgr):
    """Each sandbox gets a supervisor_port that is non-zero, not the main port
    (8090), and different from every other sandbox's port."""
    s1 = mgr.create("T001", "/project")
    s2 = mgr.create("T002", "/project")

    assert s1.supervisor_port != 0
    assert s2.supervisor_port != 0
    assert s1.supervisor_port != 8090
    assert s2.supervisor_port != 8090
    assert s1.supervisor_port != s2.supervisor_port


# ── Concurrent sandbox allocation ────────────────────────────────────────────


def test_concurrent_sandboxes(mgr):
    """Two sandboxes created concurrently must have distinct supervisor ports,
    distinct sandbox_runtime_roots, and no slot-registry corruption."""
    results: list = []
    lock = threading.Lock()

    def _create(i: int) -> None:
        s = mgr.create(f"T{i:03d}", "/project")
        with lock:
            results.append(s)

    threads = [threading.Thread(target=_create, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    supervisor_ports = [s.supervisor_port for s in results]
    runtime_roots = [s.sandbox_runtime_root for s in results]
    slots = [s.slot for s in results]

    assert len(set(supervisor_ports)) == 5, "supervisor ports must all be distinct"
    assert len(set(runtime_roots)) == 5, "runtime roots must all be distinct"
    assert len(set(slots)) == 5, "slots must all be distinct"
    assert all(p != 8090 for p in supervisor_ports), "no sandbox may reuse main port 8090"


# ── Cleanup isolation ─────────────────────────────────────────────────────────


def test_cleanup_isolates_main_runtime(mgr, tmp_path):
    """destroy() must SIGTERM the sandbox supervisor and remove the sandbox
    directory without touching the main runtime root."""
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        s = mgr.create("T001", "/project")

        # Simulate a running sandbox supervisor by writing a fake PID file.
        runtime_root = Path(s.sandbox_runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=True)
        fake_pid = 99997
        (runtime_root / "supervisor.pid").write_text(
            json.dumps({"pid": fake_pid, "port": s.supervisor_port})
        )

        with patch("services.control_api.services.sandbox_manager.os.kill") as mock_kill:
            mgr.destroy(s.id)

        # Sandbox supervisor was sent SIGTERM with the correct PID.
        mock_kill.assert_called_once_with(fake_pid, signal.SIGTERM)

    # Sandbox directory (including its runtime root) has been removed.
    assert not (mgr.sandboxes_dir / s.id).exists()

    # Main runtime root (parent of sandboxes_dir) is untouched — destroy()
    # should only remove the per-sandbox subtree, not the parent.
    assert mgr.sandboxes_dir.parent.exists()
