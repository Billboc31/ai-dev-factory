"""Tests for the async agent-layout job module and supervisor endpoints."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from fastapi.testclient import TestClient

import agent_layout_jobs as jobs


# ── jobs module unit tests ────────────────────────────────────────────────────

def test_make_job_defaults():
    job = jobs.make_job("abc", "proj", "/root", "python", "claude", "/log")
    assert job["job_id"] == "abc"
    assert job["project_id"] == "proj"
    assert job["status"] == "running"
    assert job["finished_at"] is None
    assert job["result"] is None
    assert job["log_path"] == "/log"


def test_persist_and_load_roundtrip(tmp_path):
    job = jobs.make_job("j1", "proj", "/root", "python", "claude", "/log")
    jobs.persist_job("proj", job, tmp_path)
    loaded = jobs.load_job("proj", "j1", tmp_path)
    assert loaded == job


def test_load_missing_returns_none(tmp_path):
    assert jobs.load_job("proj", "nope", tmp_path) is None


def test_list_and_latest_sorted_by_started_at(tmp_path):
    j1 = jobs.make_job("j1", "proj", "/r", "s", "c", "/l1")
    j1["started_at"] = "2026-01-01T00:00:00Z"
    j2 = jobs.make_job("j2", "proj", "/r", "s", "c", "/l2")
    j2["started_at"] = "2026-01-02T00:00:00Z"
    jobs.persist_job("proj", j1, tmp_path)
    jobs.persist_job("proj", j2, tmp_path)

    listed = jobs.list_jobs("proj", tmp_path)
    assert [j["job_id"] for j in listed] == ["j1", "j2"]
    assert jobs.latest_job("proj", tmp_path)["job_id"] == "j2"


def test_latest_empty_returns_none(tmp_path):
    assert jobs.latest_job("proj", tmp_path) is None


def test_append_and_read_log_incremental(tmp_path):
    log_path = tmp_path / "job.log"
    jobs.append_log(log_path, "line one")
    text, offset = jobs.read_log(log_path, 0)
    assert "line one" in text
    assert offset > 0

    jobs.append_log(log_path, "line two")
    text2, offset2 = jobs.read_log(log_path, offset)
    assert "line two" in text2
    assert "line one" not in text2
    assert offset2 > offset


# ── supervisor endpoint tests ─────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    from services.supervisor.main import app
    return TestClient(app)


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)
    return path


def _current_branch(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, capture_output=True, text=True,
    ).stdout.strip()


def test_start_returns_job_id_and_completes(tmp_path, client, monkeypatch):
    repo = _init_git_repo(tmp_path / "repo")

    def _fake_install(project_root, project_id, stack="unknown", exec_cmd="", log_cb=None):
        if log_cb:
            log_cb("starting fake install")
            log_cb("wrote docs/X.md")
        return {
            "branch": "docs/install", "pr_url": None, "pr_number": None,
            "docs_paths": ["docs/X.md"], "docs_count": 1,
            "analysis_summary": "ok", "warnings": [], "error": None,
        }

    monkeypatch.setattr(
        "tools.agent_runner.install_agent_layout.install_agent_layout", _fake_install,
    )

    resp = client.post(
        "/projects/proj/install-agent-layout",
        json={"project_root": str(repo), "project_id": "proj"},
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    assert job_id

    # Poll until the background thread finishes.
    final = None
    for _ in range(50):
        r = client.get(f"/projects/proj/install-agent-layout/{job_id}")
        assert r.status_code == 200
        final = r.json()
        if final["status"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert final["status"] == "done", final
    assert final["branch"] == "docs/install"

    # Logs were captured.
    logs = client.get(f"/projects/proj/install-agent-layout/{job_id}/logs").json()
    assert "fake install" in logs["text"]

    # Latest reflects this job.
    latest = client.get("/projects/proj/install-agent-layout/latest").json()
    assert latest["job_id"] == job_id


def test_start_rejects_missing_path(tmp_path, client):
    resp = client.post(
        "/projects/proj/install-agent-layout",
        json={"project_root": str(tmp_path / "nope"), "project_id": "proj"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "path_not_found"


def test_start_rejects_non_git(tmp_path, client):
    d = tmp_path / "plain"
    d.mkdir()
    resp = client.post(
        "/projects/proj/install-agent-layout",
        json={"project_root": str(d), "project_id": "proj"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "git_not_found"


def test_job_not_found_returns_404(client):
    assert client.get("/projects/proj/install-agent-layout/missing").status_code == 404
    assert client.get("/projects/proj/install-agent-layout/missing/logs").status_code == 404
    assert client.get("/projects/proj/install-agent-layout/missing/files").status_code == 404


def test_latest_with_no_jobs_returns_404(client):
    assert client.get("/projects/empty/install-agent-layout/latest").status_code == 404


def test_files_endpoint_parses_name_status(tmp_path, client, monkeypatch):
    repo = _init_git_repo(tmp_path / "repo2")
    base = _current_branch(repo)
    subprocess.run(["git", "checkout", "-b", "docs/install"], cwd=repo, capture_output=True, check=True)
    (repo / "docs").mkdir()
    (repo / "docs" / "ARCHITECTURE.md").write_text("# arch\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "docs"], cwd=repo, capture_output=True, check=True)

    runtime_root = Path(tmp_path / "runtime")
    job = jobs.make_job("jf", "proj", str(repo), "python", "claude", str(repo / "x.log"))
    job["status"] = "done"
    job["branch"] = "docs/install"
    job["result"] = {"docs_paths": ["docs/ARCHITECTURE.md"], "warnings": []}
    jobs.persist_job("proj", job, runtime_root)

    # Ensure base detection resolves to the repo's initial branch.
    assert base in ("main", "master")

    r = client.get("/projects/proj/install-agent-layout/jf/files")
    assert r.status_code == 200
    data = r.json()
    paths = [f["path"] for f in data["files"]]
    assert "docs/ARCHITECTURE.md" in paths
    entry = next(f for f in data["files"] if f["path"] == "docs/ARCHITECTURE.md")
    assert entry["status"] == "A"

    # File detail returns content + diff.
    fr = client.get(
        "/projects/proj/install-agent-layout/jf/file",
        params={"path": "docs/ARCHITECTURE.md"},
    )
    assert fr.status_code == 200
    fd = fr.json()
    assert "# arch" in fd["content"]
    assert "ARCHITECTURE.md" in fd["diff"]


def test_file_endpoint_rejects_traversal(tmp_path, client):
    runtime_root = Path(tmp_path / "runtime")
    job = jobs.make_job("jt", "proj", str(tmp_path), "python", "claude", str(tmp_path / "x.log"))
    job["status"] = "done"
    job["branch"] = "docs/install"
    jobs.persist_job("proj", job, runtime_root)

    r = client.get(
        "/projects/proj/install-agent-layout/jt/file",
        params={"path": "../../etc/passwd"},
    )
    assert r.status_code == 422
