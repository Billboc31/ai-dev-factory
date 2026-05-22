"""Integration test: supervisor `/analysis/start` rewrites container paths.

This is the regression test for the bug where the supervisor would spawn
``run_analysis.py --project-root /app`` on the host, where ``/app`` does
not exist, producing ``[Errno 2] No such file or directory: '/app'``.

The supervisor must consult ``ContainerToHostMapper`` and pass the
host-side equivalent of every container path it received from the
Dockerised control API.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def supervisor(monkeypatch, tmp_path):
    """Import a fresh supervisor with mapping env configured.

    The path_mapper reads env at instantiation time, so we must set the
    mapping variables BEFORE the module is (re)imported and the global
    ``mapper`` singleton is constructed.
    """
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", str(tmp_path / "clones" / "ai-dev-factory"))
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "runtime"))

    # Force a fresh import so the module-level `mapper` picks up the env.
    for mod in (
        "services.supervisor.main",
        "path_mapper",
    ):
        sys.modules.pop(mod, None)

    import services.supervisor.main as sup_mod  # noqa: PLC0415
    return sup_mod


def test_analysis_start_translates_container_project_root_to_host_path(
    supervisor, tmp_path,
):
    """``project_root=/app`` must be rewritten to the configured host clone."""
    client = TestClient(supervisor.app)

    captured: dict = {}

    class FakeProc:
        pid = 12345

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProc()

    with patch.object(supervisor.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(supervisor, "_sandbox_manager", None):
        resp = client.post(
            "/analysis/start",
            json={
                "project_root": "/app",
                "project_id": "myproject",
                "exec_cmd": "claude --print",
            },
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    cmd = captured["cmd"]
    # cmd looks like:
    #   [python, run_analysis.py, "--project-root", <path>, "--project-id", ..., ...]
    idx = cmd.index("--project-root")
    mapped_root = cmd[idx + 1]
    assert mapped_root != "/app", (
        "supervisor passed the unmapped container path to run_analysis.py; "
        "expected the host-side equivalent."
    )
    assert mapped_root == str(tmp_path / "clones" / "ai-dev-factory")


def test_analysis_start_translates_container_runtime_root_path(
    supervisor, tmp_path,
):
    """When the API emits a ``/runtime/...`` path (e.g. an analysis on the
    factory itself), the mapper must rewrite it to ``HOST_RUNTIME_ROOT/...``."""
    client = TestClient(supervisor.app)
    captured: dict = {}

    class FakeProc:
        pid = 1

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return FakeProc()

    with patch.object(supervisor.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(supervisor, "_sandbox_manager", None):
        resp = client.post(
            "/analysis/start",
            json={
                "project_root": "/runtime/clones/another-project",
                "project_id": "anotherproject",
                "exec_cmd": "claude --print",
            },
        )

    assert resp.status_code == 200, resp.text
    cmd = captured["cmd"]
    idx = cmd.index("--project-root")
    mapped_root = cmd[idx + 1]
    assert mapped_root == str(tmp_path / "runtime" / "clones" / "another-project")


def test_analysis_start_logs_mapping_strategy(supervisor, tmp_path, caplog):
    """The supervisor's analysis spawn must log the resolved host path."""
    import logging

    client = TestClient(supervisor.app)

    class FakeProc:
        pid = 1

    def fake_popen(cmd, *args, **kwargs):
        return FakeProc()

    with patch.object(supervisor.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(supervisor, "_sandbox_manager", None), \
         caplog.at_level(logging.INFO, logger="supervisor"):
        client.post(
            "/analysis/start",
            json={
                "project_root": "/app",
                "project_id": "logtest",
                "exec_cmd": "claude --print",
            },
        )

    messages = "\n".join(r.message for r in caplog.records)
    # Supervisor logs both the resolution result AND the path_mapper logs the
    # strategy used.
    assert "/app" in messages
    assert str(tmp_path / "clones" / "ai-dev-factory") in messages


def test_analysis_start_works_without_mapping_when_env_absent(monkeypatch, tmp_path):
    """When no mapping is configured, the supervisor falls back to identity.

    This preserves the behavior on a host-only deployment (no Docker, no
    .env file) — the supervisor still works, just without path rewriting.
    """
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    for var in (
        "CONTAINER_PROJECT_ROOT", "HOST_PROJECT_ROOT",
        "CONTAINER_RUNTIME_ROOT", "HOST_RUNTIME_ROOT",
    ):
        monkeypatch.delenv(var, raising=False)
    sys.modules.pop("services.supervisor.main", None)
    sys.modules.pop("path_mapper", None)
    import services.supervisor.main as sup_mod  # noqa: PLC0415

    captured: dict = {}

    class FakeProc:
        pid = 1

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return FakeProc()

    client = TestClient(sup_mod.app)
    with patch.object(sup_mod.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(sup_mod, "_sandbox_manager", None):
        host_path = str(tmp_path / "clones" / "myproj")
        Path(host_path).mkdir(parents=True)
        resp = client.post(
            "/analysis/start",
            json={
                "project_root": host_path,
                "project_id": "hostonly",
                "exec_cmd": "claude --print",
            },
        )

    assert resp.status_code == 200, resp.text
    idx = captured["cmd"].index("--project-root")
    assert captured["cmd"][idx + 1] == host_path
