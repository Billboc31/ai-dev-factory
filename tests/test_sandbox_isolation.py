"""Tests for concurrent sandbox isolation — unique ports, compose names, and cleanup."""

from __future__ import annotations

import sys
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
