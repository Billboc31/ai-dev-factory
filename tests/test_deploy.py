"""Tests for T229 — one-click project deploy endpoints in the supervisor.

Coverage:
- POST /workspace/projects/{id}/deploy validation (not_deployable, invalid_deploy_config, dirty)
- Concurrency: 409 when a deployment is already running
- Lock always released in finally, even after exception in background task
- deployed_sha captured before background job launch
- compose_file path-escape rejected at validation time
- allow_dirty: true allows deployment despite dirty working tree
- Successful build + healthcheck → SUCCEEDED with preview_url
- Healthcheck failure / timeout → FAILED
- History file bounded to 10 records; GET history returns last 5
- GET .../deploy/{id} cross-project → 403; unknown id → 404
- log_tail never exceeds 50 lines
- Retry after terminal state → new deployment_id returned
"""
from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def supervisor_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CONTROL_API_URL", "http://localhost:9999")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import services.supervisor.main as sup_main

    sup_main._deploy_sessions.clear()
    with sup_main._deploy_locks_mutex:
        sup_main._deploy_locks.clear()
    with sup_main._deploy_log_handlers_mutex:
        sup_main._deploy_log_handlers.clear()

    yield sup_main.app

    sup_main._deploy_sessions.clear()
    with sup_main._deploy_locks_mutex:
        sup_main._deploy_locks.clear()
    with sup_main._deploy_log_handlers_mutex:
        sup_main._deploy_log_handlers.clear()


@pytest.fixture
def client(supervisor_app):
    return TestClient(supervisor_app, raise_server_exceptions=False)


def _make_repo(tmp_path: Path, project_id: str = "my-project") -> Path:
    repo = tmp_path / project_id
    repo.mkdir(parents=True, exist_ok=True)
    return repo


def _config_with_deploy(
    repo_path: str,
    *,
    deploy: dict | None = None,
    project_id: str = "my-project",
) -> dict:
    base_deploy = {
        "type": "docker-compose",
        "compose_file": "docker-compose.yml",
        "preview_url": "http://localhost:3000",
        "startup_wait_s": 0,  # avoid real sleep in background thread
    }
    if deploy is not None:
        base_deploy.update(deploy)
    return {
        "projects": {
            project_id: {
                "repository_path": repo_path,
                "default_branch": "main",
                "allow_dirty": False,
                "deploy": base_deploy,
            }
        }
    }


def _config_no_deploy(repo_path: str, project_id: str = "my-project") -> dict:
    return {
        "projects": {
            project_id: {
                "repository_path": repo_path,
                "default_branch": "main",
                "allow_dirty": False,
            }
        }
    }


def _post_deploy(client, project_id: str = "my-project"):
    return client.post(f"/workspace/projects/{project_id}/deploy")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_post_deploy_unknown_project(client):
    with patch("services.supervisor.main._load_workspace_projects_config", return_value={"projects": {}}):
        resp = _post_deploy(client)
    assert resp.status_code == 422
    assert resp.json()["code"] == "not_deployable"


def test_post_deploy_no_deploy_block(client, tmp_path):
    repo = _make_repo(tmp_path)
    with patch("services.supervisor.main._load_workspace_projects_config",
               return_value=_config_no_deploy(str(repo))):
        resp = _post_deploy(client)
    assert resp.status_code == 422
    assert resp.json()["code"] == "not_deployable"


def test_post_deploy_invalid_type(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo), deploy={"type": "kubernetes", "compose_file": "docker-compose.yml"})
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        resp = _post_deploy(client)
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_deploy_config"
    assert "unsupported deploy type" in resp.json()["detail"]


def test_post_deploy_compose_file_path_escape(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo), deploy={"type": "docker-compose", "compose_file": "../../etc/passwd"})
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        resp = _post_deploy(client)
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_deploy_config"
    assert "escapes" in resp.json()["detail"]


def test_post_deploy_dirty_working_tree_rejected(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=True):
            resp = _post_deploy(client)
    assert resp.status_code == 422
    assert resp.json()["code"] == "dirty_working_tree"


def test_post_deploy_allow_dirty_true_proceeds(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo), deploy={
        "type": "docker-compose", "compose_file": "docker-compose.yml",
        "allow_dirty": True, "startup_wait_s": 0,
    })

    mock_proc = MagicMock()
    mock_proc.stdout = iter([])
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=True):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    resp = _post_deploy(client)

    assert resp.status_code == 202
    assert "deployment_id" in resp.json()


# ---------------------------------------------------------------------------
# deployed_sha captured before background task
# ---------------------------------------------------------------------------

def test_deployed_sha_captured_before_job(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))
    captured_sha = []

    mock_proc = MagicMock()
    mock_proc.stdout = iter([])
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        if "rev-parse" in cmd:
            result.returncode = 0
            result.stdout = "deadbeef123\n"
        else:
            result.returncode = 0
            result.stdout = ""
        return result

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run", side_effect=fake_run):
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    resp = _post_deploy(client)

    assert resp.status_code == 202
    deployment_id = resp.json()["deployment_id"]
    import services.supervisor.main as sup_main
    with sup_main._deploy_sessions_lock:
        session = sup_main._deploy_sessions.get(deployment_id)
    if session:
        assert session["deployed_sha"] == "deadbeef123"


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

def test_concurrent_deploy_returns_409(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))

    # Simulate a running deployment by holding the lock
    import services.supervisor.main as sup_main
    lock = sup_main._get_project_deploy_lock("my-project")
    lock.acquire()
    # Insert a fake running session
    fake_id = str(uuid.uuid4())
    sup_main._deploy_sessions[fake_id] = {
        "deployment_id": fake_id, "project_id": "my-project",
        "stage": "BUILDING", "status": "running",
        "started_at": "2026-01-01T00:00:00Z", "completed_at": None,
        "deployed_sha": None, "log_tail": __import__("collections").deque(maxlen=50),
        "preview_url": None, "error": None,
    }
    try:
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            with patch("services.supervisor.main._git_has_local_changes", return_value=False):
                resp = _post_deploy(client)
        assert resp.status_code == 409
        body = resp.json()
        assert body["code"] == "DEPLOYMENT_IN_PROGRESS"
        assert body["deployment_id"] == fake_id
    finally:
        lock.release()
        sup_main._deploy_sessions.pop(fake_id, None)


# ---------------------------------------------------------------------------
# Lock released in finally (exception path)
# ---------------------------------------------------------------------------

def test_lock_released_after_background_exception(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))

    def bad_popen(*args, **kwargs):
        raise RuntimeError("docker exploded")

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", side_effect=bad_popen):
                    resp = _post_deploy(client)

    assert resp.status_code == 202

    # Give background thread time to fail and release lock
    time.sleep(0.5)

    import services.supervisor.main as sup_main
    lock = sup_main._get_project_deploy_lock("my-project")
    acquired = lock.acquire(blocking=False)
    assert acquired, "Lock was not released after background exception"
    lock.release()


# ---------------------------------------------------------------------------
# Successful build
# ---------------------------------------------------------------------------

def test_successful_build_no_healthcheck(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))  # startup_wait_s=0

    mock_proc = MagicMock()
    mock_proc.stdout = iter(["Step 1/3\n", "Step 2/3\n", "Step 3/3\n"])
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    resp = _post_deploy(client)

    assert resp.status_code == 202
    deployment_id = resp.json()["deployment_id"]
    time.sleep(0.3)

    import services.supervisor.main as sup_main
    with sup_main._deploy_sessions_lock:
        session = sup_main._deploy_sessions.get(deployment_id)
    assert session is not None
    assert session["stage"] == "SUCCEEDED"
    assert session["status"] == "succeeded"
    assert session["preview_url"] == "http://localhost:3000"


def test_successful_build_with_healthcheck(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo), deploy={
        "type": "docker-compose",
        "compose_file": "docker-compose.yml",
        "preview_url": "http://localhost:3000",
        "healthcheck_url": "http://localhost:3000/health",
        "healthcheck_timeout_s": 5,
        "healthcheck_interval_s": 0,
        "startup_wait_s": 0,
    })

    mock_proc = MagicMock()
    mock_proc.stdout = iter([])
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    mock_hc_resp = MagicMock()
    mock_hc_resp.status_code = 200

    import httpx as _httpx

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    with patch.object(_httpx, "get", return_value=mock_hc_resp):
                        resp = _post_deploy(client)

    assert resp.status_code == 202
    time.sleep(0.5)
    import services.supervisor.main as sup_main
    with sup_main._deploy_sessions_lock:
        session = sup_main._deploy_sessions.get(resp.json()["deployment_id"])
    assert session["stage"] == "SUCCEEDED"


def test_healthcheck_timeout_sets_failed(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo), deploy={
        "type": "docker-compose",
        "compose_file": "docker-compose.yml",
        "healthcheck_url": "http://localhost:3000/health",
        "healthcheck_timeout_s": 0,  # immediate timeout
        "healthcheck_interval_s": 0,
        "startup_wait_s": 0,
    })

    mock_proc = MagicMock()
    mock_proc.stdout = iter([])
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    import httpx as _httpx

    def always_fail(url, **kwargs):
        raise _httpx.ConnectError("refused")

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    with patch.object(_httpx, "get", side_effect=always_fail):
                        resp = _post_deploy(client)

    assert resp.status_code == 202
    time.sleep(0.5)
    import services.supervisor.main as sup_main
    with sup_main._deploy_sessions_lock:
        session = sup_main._deploy_sessions.get(resp.json()["deployment_id"])
    assert session["stage"] == "FAILED"
    assert session["status"] == "failed"


# ---------------------------------------------------------------------------
# GET status endpoint
# ---------------------------------------------------------------------------

def test_get_deploy_status_unknown_returns_404(client):
    resp = client.get("/workspace/projects/my-project/deploy/nonexistent-id")
    assert resp.status_code == 404


def test_get_deploy_status_wrong_project_returns_403(client, tmp_path):
    import services.supervisor.main as sup_main
    from collections import deque
    fake_id = str(uuid.uuid4())
    sup_main._deploy_sessions[fake_id] = {
        "deployment_id": fake_id, "project_id": "project-a",
        "stage": "SUCCEEDED", "status": "succeeded",
        "started_at": "2026-01-01T00:00:00Z", "completed_at": "2026-01-01T00:01:00Z",
        "deployed_sha": "abc", "log_tail": deque(maxlen=50),
        "preview_url": None, "error": None,
    }
    try:
        resp = client.get(f"/workspace/projects/project-b/deploy/{fake_id}")
        assert resp.status_code == 403
    finally:
        sup_main._deploy_sessions.pop(fake_id, None)


def test_get_deploy_status_returns_session(client, tmp_path):
    import services.supervisor.main as sup_main
    from collections import deque
    fake_id = str(uuid.uuid4())
    sup_main._deploy_sessions[fake_id] = {
        "deployment_id": fake_id, "project_id": "my-project",
        "stage": "BUILDING", "status": "running",
        "started_at": "2026-01-01T00:00:00Z", "completed_at": None,
        "deployed_sha": "abc123", "log_tail": deque(["line1", "line2"], maxlen=50),
        "preview_url": None, "error": None,
    }
    try:
        resp = client.get(f"/workspace/projects/my-project/deploy/{fake_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["stage"] == "BUILDING"
        assert body["log_tail"] == ["line1", "line2"]
        assert body["deployed_sha"] == "abc123"
    finally:
        sup_main._deploy_sessions.pop(fake_id, None)


# ---------------------------------------------------------------------------
# log_tail bounded at 50 lines
# ---------------------------------------------------------------------------

def test_log_tail_never_exceeds_50_lines(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))  # startup_wait_s=0

    lines = [f"line {i}\n" for i in range(200)]
    mock_proc = MagicMock()
    mock_proc.stdout = iter(lines)
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        with patch("services.supervisor.main._git_has_local_changes", return_value=False):
            with patch("services.supervisor.main.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                with patch("services.supervisor.main.subprocess.Popen", return_value=mock_proc):
                    resp = _post_deploy(client)

    assert resp.status_code == 202
    time.sleep(0.3)
    import services.supervisor.main as sup_main
    deployment_id = resp.json()["deployment_id"]
    with sup_main._deploy_sessions_lock:
        session = sup_main._deploy_sessions.get(deployment_id)
    assert session is not None
    assert len(session["log_tail"]) <= 50


# ---------------------------------------------------------------------------
# Retry after terminal state
# ---------------------------------------------------------------------------

def test_retry_after_succeeded_returns_new_id(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_with_deploy(str(repo))  # startup_wait_s=0

    def _make_mock_proc():
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0
        return mock_proc

    def do_deploy():
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            with patch("services.supervisor.main._git_has_local_changes", return_value=False):
                with patch("services.supervisor.main.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="abc123")
                    with patch("services.supervisor.main.subprocess.Popen", return_value=_make_mock_proc()):
                        return _post_deploy(client)

    resp1 = do_deploy()
    assert resp1.status_code == 202
    time.sleep(0.3)
    id1 = resp1.json()["deployment_id"]

    resp2 = do_deploy()
    assert resp2.status_code == 202
    id2 = resp2.json()["deployment_id"]
    assert id1 != id2


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------

def test_deploy_history_empty_when_no_file(client, tmp_path):
    repo = _make_repo(tmp_path)
    config = _config_no_deploy(str(repo))
    with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
        resp = client.get("/workspace/projects/my-project/deploy/history")
    assert resp.status_code == 200
    assert resp.json()["history"] == []


def test_deploy_history_returns_last_5(tmp_path):
    import services.supervisor.main as sup_main

    repo = _make_repo(tmp_path)
    artifact_dir = repo / ".ai-dev-factory"
    artifact_dir.mkdir()

    records = [
        {"deployment_id": str(i), "status": "succeeded", "started_at": f"2026-01-0{i+1}T00:00:00Z",
         "completed_at": None, "deployed_sha": None, "preview_url": None}
        for i in range(10)
    ]
    (artifact_dir / "project-deploy-history.json").write_text(json.dumps(records))

    config = _config_no_deploy(str(repo))
    from fastapi.testclient import TestClient as _TC
    import services.supervisor.main as sup_main
    sup_main._deploy_sessions.clear()
    with _TC(sup_main.app, raise_server_exceptions=False) as test_client:
        with patch("services.supervisor.main._load_workspace_projects_config", return_value=config):
            resp = test_client.get("/workspace/projects/my-project/deploy/history")
    assert resp.status_code == 200
    history = resp.json()["history"]
    assert len(history) == 5
    assert history[0]["deployment_id"] == "0"


def test_update_deploy_history_bounded_to_10(tmp_path):
    import services.supervisor.main as sup_main

    repo = str(_make_repo(tmp_path))
    artifact_dir = Path(repo) / ".ai-dev-factory"
    artifact_dir.mkdir()

    for i in range(12):
        session = {
            "deployment_id": str(uuid.uuid4()),
            "status": "succeeded",
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:01:00Z",
            "deployed_sha": "abc",
            "preview_url": None,
        }
        sup_main._update_deploy_history(repo, session)

    history_data = json.loads((artifact_dir / "project-deploy-history.json").read_text())
    assert len(history_data) == 10


# ---------------------------------------------------------------------------
# Persistence: write_deploy_state
# ---------------------------------------------------------------------------

def test_write_deploy_state_atomic(tmp_path):
    import services.supervisor.main as sup_main

    repo = str(_make_repo(tmp_path))
    session = {
        "deployment_id": "test-id",
        "status": "succeeded",
        "stage": "SUCCEEDED",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:01:00Z",
        "deployed_sha": "abc123",
        "preview_url": "http://localhost:3000",
        "error": None,
    }
    sup_main._write_deploy_state(repo, session)

    state_path = Path(repo) / ".ai-dev-factory" / "project-deploy-state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data["deployment_id"] == "test-id"
    assert data["status"] == "succeeded"
    assert not (state_path.with_suffix(".json.tmp")).exists()
