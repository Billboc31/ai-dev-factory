"""Tests for the redeploy_project capability in the supervisor workspace endpoints.

Coverage:
- Config helpers: load_config_missing, load_config_valid, git_has_local_changes variants
- Proposal-time validation: unknown project, unknown component, branch param ignored, dirty warning
- Confirmation: background job start, concurrent 409, unknown action 404
- Background job execution: all failure modes and success path
- Supervisor status polling endpoint
"""
from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "supervisor"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def supervisor_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CONTROL_API_URL", "http://localhost:9999")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import services.supervisor.main as sup_main

    sup_main._pending_workspace_actions.clear()
    sup_main._pending_workspace_issues.clear()
    sup_main._deployment_jobs.clear()
    # Reset per-project locks to prevent cross-test contamination from mock threads
    with sup_main._workspace_redeploy_locks_mutex:
        sup_main._workspace_redeploy_locks.clear()

    yield sup_main.app

    sup_main._pending_workspace_actions.clear()
    sup_main._pending_workspace_issues.clear()
    sup_main._deployment_jobs.clear()
    with sup_main._workspace_redeploy_locks_mutex:
        sup_main._workspace_redeploy_locks.clear()


@pytest.fixture
def client(supervisor_app):
    return TestClient(supervisor_app, raise_server_exceptions=False)


def _valid_config(repo_path: str = "/repo/timizer") -> dict:
    return {
        "projects": {
            "timizer": {
                "display_name": "Timizer",
                "repository_path": repo_path,
                "default_branch": "main",
                "allow_dirty": False,
                "redeploy": {
                    "backend": {"service": "backend"},
                    "frontend": {"service": "frontend"},
                },
                "preview_url": "http://localhost:3000",
            }
        }
    }


def _ai_response(**overrides) -> dict:
    base = {
        "reply": "I will redeploy the project.",
        "intent": "actionable",
        "proposed_action": {
            "capability": "redeploy_project",
            "description": "Pull and redeploy backend and frontend",
            "params": {"pull": True, "components": ["backend", "frontend"]},
        },
        "issue_draft": None,
        "confirmation_required": True,
    }
    base.update(overrides)
    return base


def _post_chat(client, project_id: str, ai_return: dict):
    with patch("services.supervisor.main._call_workspace_ai", return_value=ai_return):
        return client.post(
            f"/workspace/projects/{project_id}/chat",
            json={"message": "redeploy", "conversation_history": []},
        )


# ---------------------------------------------------------------------------
# Config and helpers
# ---------------------------------------------------------------------------

def test_load_config_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_PROJECTS_CONFIG", str(tmp_path / "nonexistent.yml"))
    import services.supervisor.main as sup_main
    assert sup_main._load_workspace_projects_config() == {}


def test_load_config_valid(tmp_path, monkeypatch):
    config_file = tmp_path / "projects.yml"
    config_file.write_text(
        "projects:\n  timizer:\n    repository_path: /repo\n    default_branch: main\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WORKSPACE_PROJECTS_CONFIG", str(config_file))
    import services.supervisor.main as sup_main
    result = sup_main._load_workspace_projects_config()
    assert result["projects"]["timizer"]["repository_path"] == "/repo"


def test_git_has_local_changes_clean():
    import services.supervisor.main as sup_main
    completed = MagicMock()
    completed.stdout = ""
    with patch("services.supervisor.main.subprocess.run", return_value=completed):
        assert sup_main._git_has_local_changes("/repo") is False


def test_git_has_local_changes_dirty():
    import services.supervisor.main as sup_main
    completed = MagicMock()
    completed.stdout = " M services/foo.py\n"
    with patch("services.supervisor.main.subprocess.run", return_value=completed):
        assert sup_main._git_has_local_changes("/repo") is True


def test_git_has_local_changes_not_a_repo():
    import services.supervisor.main as sup_main
    with patch("services.supervisor.main.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            sup_main._git_has_local_changes("/nonexistent")


# ---------------------------------------------------------------------------
# Proposal-time validation
# ---------------------------------------------------------------------------

def test_chat_unknown_project_returns_informational(client):
    with patch("services.supervisor.main._load_workspace_projects_config", return_value={"projects": {}}):
        resp = _post_chat(client, "unknown-proj", _ai_response())
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "informational"
    assert body["proposed_action"] is None
    assert body["confirmation_required"] is False


def test_chat_unknown_component_rejected(client):
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=_valid_config()):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            ai_ret = _ai_response()
            ai_ret["proposed_action"]["params"]["components"] = ["database"]
            resp = _post_chat(client, "timizer", ai_ret)
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "informational"
    assert body["proposed_action"] is None


def test_chat_branch_param_ignored(client):
    """LLM-provided branch must be stripped; only configured branch is used."""
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=_valid_config()):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            ai_ret = _ai_response()
            ai_ret["proposed_action"]["params"]["branch"] = "feature/evil"
            resp = _post_chat(client, "timizer", ai_ret)
    assert resp.status_code == 200
    body = resp.json()
    assert body["proposed_action"]["configured_branch"] == "main"
    assert "branch" not in body["proposed_action"].get("params", {})


def test_chat_has_dirty_warning_propagated(client):
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=_valid_config()):
        with patch("services.supervisor.main._git_has_local_changes", return_value=True):
            resp = _post_chat(client, "timizer", _ai_response())
    assert resp.status_code == 200
    assert resp.json()["proposed_action"]["has_dirty_warning"] is True


# ---------------------------------------------------------------------------
# Confirmation and lock
# ---------------------------------------------------------------------------

def _inject_action(project_id: str, components=None, pull=True) -> str:
    import services.supervisor.main as sup_main
    action_id = str(uuid.uuid4())
    with sup_main._workspace_lock:
        sup_main._pending_workspace_actions[action_id] = {
            "project_id": project_id,
            "capability": "redeploy_project",
            "description": "Redeploy",
            "params": {"pull": pull, "components": components or ["backend", "frontend"]},
            "has_dirty_warning": False,
            "created_at": "2026-01-01T00:00:00Z",
        }
    return action_id


def test_confirm_starts_background_job(client):
    import services.supervisor.main as sup_main
    action_id = _inject_action("timizer")

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=_valid_config()):
        with patch("services.supervisor.main.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            resp = client.post(
                "/workspace/projects/timizer/actions/confirm",
                json={"action_id": action_id},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "deployment_id" in body
    assert body["status"] == "RUNNING"
    assert action_id not in sup_main._pending_workspace_actions


def test_confirm_concurrent_returns_409(client):
    import services.supervisor.main as sup_main
    action_id = _inject_action("timizer")

    # Pre-acquire the lock to simulate a running deployment
    lock = sup_main._get_redeploy_lock("timizer")
    lock.acquire()
    try:
        resp = client.post(
            "/workspace/projects/timizer/actions/confirm",
            json={"action_id": action_id},
        )
    finally:
        lock.release()

    assert resp.status_code == 409


def test_confirm_unknown_action_id_returns_404(client):
    resp = client.post(
        "/workspace/projects/timizer/actions/confirm",
        json={"action_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Background job execution
# ---------------------------------------------------------------------------

def _run_job_sync(project_id: str, components: list, pull: bool, config: dict, subproc_side_effects: list | None = None):
    """Helper: run _run_redeploy_job synchronously and return job state."""
    import services.supervisor.main as sup_main

    deployment_id = str(uuid.uuid4())
    lock = threading.Lock()
    lock.acquire()  # simulate held lock at job start

    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id,
            "project_id": project_id,
            "status": "RUNNING",
            "stage": None,
            "started_at": now,
            "completed_at": None,
            "result_message": None,
            "deployed_sha": None,
            "preview_url": None,
            "error_stage": None,
            "error_excerpt": None,
        }

    patches = [patch("services.supervisor.main._load_workspace_projects_config", return_value=config)]
    if subproc_side_effects is not None:
        patches.append(patch("services.supervisor.main.subprocess.run", side_effect=subproc_side_effects))

    for p in patches:
        p.start()

    sup_main._run_redeploy_job(deployment_id, project_id, components, pull, lock)

    for p in patches:
        p.stop()

    with sup_main._deployment_jobs_lock:
        job = dict(sup_main._deployment_jobs[deployment_id])

    return job, lock


def _make_subproc(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_job_branch_mismatch_rejected(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    # git branch --show-current returns "feature/other"
    branch_result = _make_subproc(returncode=0, stdout="feature/other")
    job, lock = _run_job_sync("timizer", ["backend"], True, config, [branch_result])

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "BRANCH_MISMATCH"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False), "lock must be released"
    lock.release()


def test_job_dirty_between_proposal_and_confirm(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    # git branch returns "main", git status returns dirty
    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout=" M file.py\n")
    job, lock = _run_job_sync("timizer", ["backend"], True, config, [branch_result, dirty_result])

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "DIRTY_CHECK"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_pull_failure_stops_early(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=1, stderr="fatal: could not read from remote")
    job, lock = _run_job_sync("timizer", ["backend"], True, config, [branch_result, dirty_result, pull_result])

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "PULLING"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_first_component_failure_stops_loop(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0, stdout="Already up to date.")
    backend_fail = _make_subproc(returncode=1, stderr="Error building backend")

    job, lock = _run_job_sync(
        "timizer", ["backend", "frontend"], True, config,
        [branch_result, dirty_result, pull_result, backend_fail],
    )

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "BUILDING_backend"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_backend_only(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)
    backend_ok = _make_subproc(returncode=0)
    sha_result = _make_subproc(returncode=0, stdout="abc1234")

    with patch("services.supervisor.main.subprocess.run", side_effect=[branch_result, dirty_result, pull_result, backend_ok, sha_result]) as mock_run:
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            import datetime as _dt
            deployment_id = str(uuid.uuid4())
            lock = threading.Lock()
            lock.acquire()
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            with sup_main._deployment_jobs_lock:
                sup_main._deployment_jobs[deployment_id] = {
                    "deployment_id": deployment_id, "project_id": "timizer",
                    "status": "RUNNING", "stage": None, "started_at": now,
                    "completed_at": None, "result_message": None, "deployed_sha": None,
                    "preview_url": None, "error_stage": None, "error_excerpt": None,
                }
            sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    # Verify docker compose called exactly once for backend service
    compose_calls = [c for c in mock_run.call_args_list if "compose" in str(c)]
    assert len(compose_calls) == 1
    assert "backend" in str(compose_calls[0])
    assert "frontend" not in str(compose_calls[0])

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "SUCCEEDED"
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_frontend_only(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    frontend_ok = _make_subproc(returncode=0)
    sha_result = _make_subproc(returncode=0, stdout="abc1234")

    with patch("services.supervisor.main.subprocess.run", side_effect=[branch_result, dirty_result, frontend_ok, sha_result]) as mock_run:
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            import datetime as _dt
            deployment_id = str(uuid.uuid4())
            lock = threading.Lock()
            lock.acquire()
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            with sup_main._deployment_jobs_lock:
                sup_main._deployment_jobs[deployment_id] = {
                    "deployment_id": deployment_id, "project_id": "timizer",
                    "status": "RUNNING", "stage": None, "started_at": now,
                    "completed_at": None, "result_message": None, "deployed_sha": None,
                    "preview_url": None, "error_stage": None, "error_excerpt": None,
                }
            sup_main._run_redeploy_job(deployment_id, "timizer", ["frontend"], False, lock)

    compose_calls = [c for c in mock_run.call_args_list if "compose" in str(c)]
    assert len(compose_calls) == 1
    assert "frontend" in str(compose_calls[0])

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "SUCCEEDED"
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_success_returns_sha_and_url(tmp_path):
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)
    backend_ok = _make_subproc(returncode=0)
    frontend_ok = _make_subproc(returncode=0)
    sha_result = _make_subproc(returncode=0, stdout="abc1234")

    job, lock = _run_job_sync(
        "timizer", ["backend", "frontend"], True, config,
        [branch_result, dirty_result, pull_result, backend_ok, frontend_ok, sha_result],
    )

    assert job["status"] == "SUCCEEDED"
    assert job["deployed_sha"] == "abc1234"
    assert job["preview_url"] == "http://localhost:3000"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_lock_released_after_failure(tmp_path):
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=1, stderr="not a git repo")
    job, lock = _run_job_sync("timizer", ["backend"], True, config, [branch_result])

    assert job["status"] == "FAILED"
    assert lock.acquire(blocking=False), "lock must be released after failure"
    lock.release()


def test_job_lock_released_after_exception(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    import datetime as _dt
    deployment_id = str(uuid.uuid4())
    lock = threading.Lock()
    lock.acquire()
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id, "project_id": "timizer",
            "status": "RUNNING", "stage": None, "started_at": now,
            "completed_at": None, "result_message": None, "deployed_sha": None,
            "preview_url": None, "error_stage": None, "error_excerpt": None,
        }

    with patch("services.supervisor.main._load_workspace_projects_config", side_effect=RuntimeError("boom")):
        sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "INTERNAL_ERROR"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False), "lock must be released after exception"
    lock.release()


def test_job_git_timeout(tmp_path):
    import subprocess
    repo = str(tmp_path)
    config = _valid_config(repo)

    with patch("services.supervisor.main.subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 10)):
        job, lock = _run_job_sync("timizer", ["backend"], True, config, None)

    assert job["status"] == "FAILED"
    assert "TIMEOUT" in job["error_stage"] or "CHECK" in job["error_stage"]
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_compose_timeout(tmp_path):
    import subprocess as _subprocess
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)

    with patch("services.supervisor.main.subprocess.run", side_effect=[
        branch_result, dirty_result, pull_result,
        _subprocess.TimeoutExpired(["docker"], 300),
    ]):
        import datetime as _dt
        import services.supervisor.main as sup_main
        deployment_id = str(uuid.uuid4())
        lock = threading.Lock()
        lock.acquire()
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        with sup_main._deployment_jobs_lock:
            sup_main._deployment_jobs[deployment_id] = {
                "deployment_id": deployment_id, "project_id": "timizer",
                "status": "RUNNING", "stage": None, "started_at": now,
                "completed_at": None, "result_message": None, "deployed_sha": None,
                "preview_url": None, "error_stage": None, "error_excerpt": None,
            }
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "FAILED"
    assert "BUILDING" in job["error_stage"]
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_git_not_found(tmp_path):
    repo = str(tmp_path)
    config = _valid_config(repo)

    with patch("services.supervisor.main.subprocess.run", side_effect=FileNotFoundError):
        job, lock = _run_job_sync("timizer", ["backend"], True, config, None)

    assert job["status"] == "FAILED"
    assert "GIT_NOT_FOUND" in job["error_stage"]
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_docker_not_found(tmp_path):
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)

    import datetime as _dt
    deployment_id = str(uuid.uuid4())
    lock = threading.Lock()
    lock.acquire()
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id, "project_id": "timizer",
            "status": "RUNNING", "stage": None, "started_at": now,
            "completed_at": None, "result_message": None, "deployed_sha": None,
            "preview_url": None, "error_stage": None, "error_excerpt": None,
        }

    with patch("services.supervisor.main.subprocess.run", side_effect=[
        branch_result, dirty_result, pull_result, FileNotFoundError(),
    ]):
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "FAILED"
    assert "BUILDING" in job["error_stage"]
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_path_not_exist():
    config = _valid_config("/nonexistent/path")
    job, lock = _run_job_sync("timizer", ["backend"], True, config, [])
    assert job["status"] == "FAILED"
    assert job["error_stage"] == "PATH_NOT_FOUND"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_config_reloaded_at_execution(tmp_path):
    """Stale repo_path in pending action is not used; fresh config is loaded."""
    import services.supervisor.main as sup_main

    # Config at execution time has a DIFFERENT repo path
    new_repo = str(tmp_path)
    config = _valid_config(new_repo)
    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)
    backend_ok = _make_subproc(returncode=0)
    sha_result = _make_subproc(returncode=0, stdout="abc1234")

    captured_cwds = []

    def fake_run(cmd, *args, **kwargs):
        captured_cwds.append(kwargs.get("cwd"))
        idx = len(captured_cwds) - 1
        return [branch_result, dirty_result, pull_result, backend_ok, sha_result][idx]

    import datetime as _dt
    deployment_id = str(uuid.uuid4())
    lock = threading.Lock()
    lock.acquire()
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id, "project_id": "timizer",
            "status": "RUNNING", "stage": None, "started_at": now,
            "completed_at": None, "result_message": None, "deployed_sha": None,
            "preview_url": None, "error_stage": None, "error_excerpt": None,
        }

    with patch("services.supervisor.main.subprocess.run", side_effect=fake_run):
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    # All subprocess calls must use the config-derived path, not any stale path
    for cwd in captured_cwds:
        if cwd is not None:
            assert cwd == new_repo

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "SUCCEEDED"
    lock.acquire(blocking=False)
    lock.release()


def test_job_stale_service_name_ignored(tmp_path):
    """Service name comes from config, not from the pending action."""
    import services.supervisor.main as sup_main
    repo = str(tmp_path)
    config = _valid_config(repo)

    branch_result = _make_subproc(returncode=0, stdout="main")
    dirty_result = _make_subproc(returncode=0, stdout="")
    pull_result = _make_subproc(returncode=0)
    backend_ok = _make_subproc(returncode=0)
    sha_result = _make_subproc(returncode=0, stdout="def5678")

    with patch("services.supervisor.main.subprocess.run", side_effect=[branch_result, dirty_result, pull_result, backend_ok, sha_result]) as mock_run:
        import datetime as _dt
        deployment_id = str(uuid.uuid4())
        lock = threading.Lock()
        lock.acquire()
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        with sup_main._deployment_jobs_lock:
            sup_main._deployment_jobs[deployment_id] = {
                "deployment_id": deployment_id, "project_id": "timizer",
                "status": "RUNNING", "stage": None, "started_at": now,
                "completed_at": None, "result_message": None, "deployed_sha": None,
                "preview_url": None, "error_stage": None, "error_excerpt": None,
            }
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            # Pass a tampered service name — it must not be used
            sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    compose_calls = [c for c in mock_run.call_args_list if "compose" in str(c)]
    assert len(compose_calls) == 1
    assert "backend" in str(compose_calls[0])  # service from config, not tampered

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]
    assert job["status"] == "SUCCEEDED"
    lock.acquire(blocking=False)
    lock.release()


def test_job_config_missing_at_execution():
    job, lock = _run_job_sync("timizer", ["backend"], True, {"projects": {}}, [])
    assert job["status"] == "FAILED"
    assert job["error_stage"] == "CONFIG_MISSING"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


def test_job_terminal_state_always_set():
    """Unexpected exception → FAILED, completed_at set, error_stage=INTERNAL_ERROR."""
    import services.supervisor.main as sup_main

    import datetime as _dt
    deployment_id = str(uuid.uuid4())
    lock = threading.Lock()
    lock.acquire()
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id, "project_id": "timizer",
            "status": "RUNNING", "stage": None, "started_at": now,
            "completed_at": None, "result_message": None, "deployed_sha": None,
            "preview_url": None, "error_stage": None, "error_excerpt": None,
        }

    with patch("services.supervisor.main._load_workspace_projects_config", side_effect=ValueError("unexpected")):
        sup_main._run_redeploy_job(deployment_id, "timizer", ["backend"], True, lock)

    with sup_main._deployment_jobs_lock:
        job = sup_main._deployment_jobs[deployment_id]

    assert job["status"] == "FAILED"
    assert job["error_stage"] == "INTERNAL_ERROR"
    assert job["completed_at"] is not None
    assert lock.acquire(blocking=False)
    lock.release()


# ---------------------------------------------------------------------------
# Supervisor status polling endpoint
# ---------------------------------------------------------------------------

def _inject_job(deployment_id: str, project_id: str, status: str, **extra):
    import services.supervisor.main as sup_main
    import datetime as _dt
    with sup_main._deployment_jobs_lock:
        sup_main._deployment_jobs[deployment_id] = {
            "deployment_id": deployment_id,
            "project_id": project_id,
            "status": status,
            "stage": extra.get("stage"),
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": extra.get("completed_at"),
            "result_message": extra.get("result_message"),
            "deployed_sha": extra.get("deployed_sha"),
            "preview_url": extra.get("preview_url"),
            "error_stage": extra.get("error_stage"),
            "error_excerpt": extra.get("error_excerpt"),
        }


def test_get_deployment_status_running(client):
    dep_id = str(uuid.uuid4())
    _inject_job(dep_id, "timizer", "RUNNING", stage="PULLING")
    resp = client.get(f"/workspace/projects/timizer/deployments/{dep_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "RUNNING"
    assert resp.json()["stage"] == "PULLING"


def test_get_deployment_status_succeeded(client):
    dep_id = str(uuid.uuid4())
    _inject_job(dep_id, "timizer", "SUCCEEDED",
                deployed_sha="abc1234", preview_url="http://localhost:3000",
                completed_at="2026-01-01T00:01:00Z")
    resp = client.get(f"/workspace/projects/timizer/deployments/{dep_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SUCCEEDED"
    assert body["deployed_sha"] == "abc1234"
    assert body["preview_url"] == "http://localhost:3000"


def test_get_deployment_status_project_mismatch(client):
    dep_id = str(uuid.uuid4())
    _inject_job(dep_id, "timizer", "RUNNING")
    resp = client.get(f"/workspace/projects/other-project/deployments/{dep_id}")
    assert resp.status_code == 404


def test_get_deployment_status_unknown(client):
    resp = client.get(f"/workspace/projects/timizer/deployments/{uuid.uuid4()}")
    assert resp.status_code == 404
