"""Item 1 (no split-brain): the supervisor must spawn project daemons with the
same Postgres backend config AND the correct project_id, so API + supervisor +
daemon all read/write the same project-scoped runtime state.

Proven without real processes by capturing the subprocess.Popen command + env.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.supervisor import main as sup


class _FakeProc:
    def __init__(self, pid=4242):
        self.pid = pid

    def poll(self):
        return None


@pytest.fixture()
def captured_spawn(tmp_path, monkeypatch):
    """Stub out filesystem + Popen so project_daemon_start can run in isolation."""
    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        captured["cwd"] = kwargs.get("cwd")
        return _FakeProc()

    monkeypatch.setattr(sup.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sup, "_lookup_project_root_from_control_api", lambda pid: str(tmp_path / pid))
    monkeypatch.setattr(sup, "_project_runtime_root", lambda pid: tmp_path / pid / "runtime")
    monkeypatch.setattr(sup, "_project_runs_dir", lambda pid: tmp_path / pid / "runs")
    monkeypatch.setattr(sup, "_project_logs_dir", lambda pid: tmp_path / pid / "logs")
    monkeypatch.setattr(sup, "_project_state_dir", lambda pid: tmp_path / pid / "state")
    monkeypatch.setattr(sup, "_project_worktrees_dir", lambda pid: tmp_path / pid / "worktrees")
    monkeypatch.setattr(sup, "_project_pid_path", lambda pid: tmp_path / pid / "daemon.pid")
    monkeypatch.setattr(sup, "_project_log_path", lambda pid: tmp_path / pid / "logs" / "daemon.log")
    monkeypatch.setattr(sup, "_write_project_pid_file", lambda *a, **k: None)
    # Ensure a clean per-project state for each run.
    sup._project_daemon_states.clear()
    sup._project_daemon_procs.clear()
    return captured


def test_project_daemon_receives_project_id_and_pg_env(captured_spawn, monkeypatch):
    # Supervisor environment configured for Postgres (as deploy/.env would).
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("RUNTIME_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("RUNTIME_DB_PORT", "5432")
    monkeypatch.setenv("RUNTIME_DB_USER", "adf")
    monkeypatch.setenv("RUNTIME_DB_PASSWORD", "adf")
    monkeypatch.setenv("RUNTIME_DB_NAME", "adf")
    # The supervisor's own PROJECT_NAME is ai-dev-factory — the daemon must NOT
    # inherit it for a different project.
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")

    body = sup.ProjectDaemonStartRequest()
    result = sup.project_daemon_start("test-ai-dev", body)
    assert result["ok"] is True

    cmd = captured_spawn["cmd"]
    env = captured_spawn["env"]

    # project_id is passed explicitly so runtime DB rows are scoped correctly.
    assert "--project" in cmd
    assert cmd[cmd.index("--project") + 1] == "test-ai-dev"

    # Pin GitHub intake to the managed project's origin (not ambient cwd/gh defaults).
    assert "--issue-repo" in cmd

    # PROJECT_NAME is overridden to the target project (not the supervisor's).
    assert env["PROJECT_NAME"] == "test-ai-dev"

    # The daemon inherits the same Postgres backend config as API + supervisor.
    assert env["RUNTIME_DB_BACKEND"] == "postgres"
    for key in ("RUNTIME_DB_HOST", "RUNTIME_DB_PORT", "RUNTIME_DB_USER", "RUNTIME_DB_PASSWORD", "RUNTIME_DB_NAME"):
        assert key in env, f"daemon env missing {key}"
