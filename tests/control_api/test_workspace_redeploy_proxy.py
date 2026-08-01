"""Control API proxy tests for the T227 redeploy_project workspace routes.

Verifies that:
- Supervisor 200 → Control API 200 with unchanged body
- Supervisor 409 → Control API 409 (not silently collapsed)
- Supervisor 404 → Control API 404
- Unknown project_id → 404 before forwarding (project-resolution dependency)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

_PROJECT_ID = "my-project"


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    project_root = tmp_path / _PROJECT_ID
    project_root.mkdir()
    return create_app(project_root=project_root)


@pytest.fixture
def app(tmp_path):
    return _make_app(tmp_path)


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_supervisor_response(status_code: int, body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = json.dumps(body)
    resp.headers = {"content-type": "application/json"}
    return resp


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/workspace/deployments/{deployment_id}
# ---------------------------------------------------------------------------

def test_proxy_polling_200(client):
    """Supervisor returns 200 with job state → Control API returns 200 with unchanged body."""
    supervisor_body = {
        "deployment_id": "dep-123",
        "project_id": "my-project",
        "status": "RUNNING",
        "stage": "PULLING",
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": None,
        "result_message": None,
        "deployed_sha": None,
        "preview_url": None,
        "error_stage": None,
        "error_excerpt": None,
    }
    mock_resp = _mock_supervisor_response(200, supervisor_body)

    with patch("services.control_api.routes.workspace.httpx.get", return_value=mock_resp):
        resp = client.get("/projects/my-project/workspace/deployments/dep-123")

    assert resp.status_code == 200
    assert resp.json() == supervisor_body


def test_proxy_supervisor_409_becomes_control_api_409(client):
    """Supervisor returns 409 → Control API must return 409, not silently collapse to 200."""
    supervisor_body = {"detail": "deployment already running for project"}
    mock_resp = _mock_supervisor_response(409, supervisor_body)

    with patch("services.control_api.routes.workspace.httpx.post", return_value=mock_resp):
        resp = client.post(
            "/projects/my-project/workspace/actions/confirm",
            json={"action_id": "some-action-id"},
        )

    assert resp.status_code == 409


def test_proxy_supervisor_404_becomes_control_api_404(client):
    """Supervisor returns 404 → Control API returns 404."""
    supervisor_body = {"detail": "deployment not found"}
    mock_resp = _mock_supervisor_response(404, supervisor_body)

    with patch("services.control_api.routes.workspace.httpx.get", return_value=mock_resp):
        resp = client.get("/projects/my-project/workspace/deployments/unknown-dep")

    assert resp.status_code == 404


def test_proxy_unknown_project_returns_404(client):
    """project_id that fails the resolve_project dependency → 404 without forwarding."""
    # Do not mock httpx — if it's called the test fails because no real supervisor is up
    resp = client.get("/projects/nonexistent-project/workspace/deployments/dep-123")
    assert resp.status_code == 404
