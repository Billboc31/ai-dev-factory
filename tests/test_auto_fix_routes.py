"""Integration tests for auto-fix API routes.

Cases covered:
1. propose_auto_fix — proxies to supervisor and returns proposal_id
2. get_proposal — 404 when supervisor has no such proposal
3. list_proposals — returns empty list when no proposals exist
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / ".git").mkdir()
    return create_app(project_root=proj, projects_root=tmp_path)


# ── 1. propose — happy path: proxies to supervisor ───────────────────────────

def test_propose_returns_proposal_id(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://supervisor:9000")

    from fastapi.testclient import TestClient
    from services.control_api.services import auto_fix_runner

    def fake_propose(**kwargs):
        return {"ok": True, "proposal_id": "abc123456789"}

    monkeypatch.setattr(auto_fix_runner, "propose_auto_fix", lambda **kw: fake_propose(**kw))

    app = _make_app(tmp_path)
    client = TestClient(app)

    proj_id = Path(tmp_path / "myproject").name
    r = client.post(
        f"/projects/{proj_id}/auto-fix/propose",
        json={"exec_cmd": "echo", "sandbox_id": "sb1", "failing_step": "build.sh"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "proposal_id" in data


# ── 2. get_proposal — 404 when proposal is missing ───────────────────────────

def test_get_proposal_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://supervisor:9000")

    from fastapi.testclient import TestClient
    from services.control_api.services import auto_fix_runner

    monkeypatch.setattr(auto_fix_runner, "get_proposal", lambda *a, **kw: None)

    app = _make_app(tmp_path)
    client = TestClient(app)

    proj_id = Path(tmp_path / "myproject").name
    r = client.get(f"/projects/{proj_id}/auto-fix/proposal/notexist")
    assert r.status_code == 404


# ── 3. list_proposals — empty list when no proposals ─────────────────────────

def test_list_proposals_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_SUPERVISOR_URL", "http://supervisor:9000")

    from fastapi.testclient import TestClient
    from services.control_api.services import auto_fix_runner

    monkeypatch.setattr(auto_fix_runner, "list_proposals", lambda *a, **kw: [])

    app = _make_app(tmp_path)
    client = TestClient(app)

    proj_id = Path(tmp_path / "myproject").name
    r = client.get(f"/projects/{proj_id}/auto-fix/proposals")
    assert r.status_code == 200
    assert r.json() == {"proposals": []}
