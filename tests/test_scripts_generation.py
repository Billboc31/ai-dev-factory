"""Tests for the scripts generation feature.

Covers:
- scripts_prompt_builder: expected FILE blocks present in prompt
- run_scripts: success path, missing FILE block error, path traversal, LLM failure
- scripts_git_service: branch naming, gh pr create/update invocation
- scripts_manager: HTTP proxy to supervisor
- deployer routes: generate-scripts, scripts/status, scripts/logs endpoints
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── scripts_prompt_builder ────────────────────────────────────────────────────

from scripts_prompt_builder import build_scripts_prompt  # noqa: E402

_MOCK_SCAN = {
    "docker_services": ["api", "web"],
    "python_backend": True,
    "node_frontend": True,
    "required_tools": ["git", "docker"],
}

_EXPECTED_FILE_BLOCKS = [
    ".ai-dev-factory/scripts/bootstrap.sh",
    ".ai-dev-factory/scripts/build.sh",
    ".ai-dev-factory/scripts/start.sh",
    ".ai-dev-factory/scripts/stop.sh",
    ".ai-dev-factory/scripts/restart.sh",
    ".ai-dev-factory/scripts/healthcheck.sh",
    ".ai-dev-factory/deployment.md",
]


def test_prompt_contains_all_required_file_blocks():
    prompt = build_scripts_prompt("/project", _MOCK_SCAN, "version: 1\n", "project/\n└── src/")
    for path in _EXPECTED_FILE_BLOCKS:
        assert path in prompt, f"expected FILE block for {path!r} not found in prompt"


def test_prompt_contains_scan_json():
    prompt = build_scripts_prompt("/project", _MOCK_SCAN, "", "tree")
    assert "python_backend" in prompt
    assert '"api"' in prompt


def test_prompt_uses_deploy_profile_yaml():
    prompt = build_scripts_prompt("/project", _MOCK_SCAN, "version: 1\nproject: myapp\n", "tree")
    assert "myapp" in prompt


def test_prompt_fallback_when_no_deploy_profile():
    prompt = build_scripts_prompt("/project", _MOCK_SCAN, "", "tree")
    assert "(not available)" in prompt


def test_prompt_contains_hard_constraints_block():
    """The prompt must spell out the rules that caused PR #114 to fail
    (markdown fences inside scripts, prose-as-script, summary deployment.md).
    Otherwise the LLM keeps re-producing the same broken outputs."""
    prompt = build_scripts_prompt("/project", _MOCK_SCAN, "", "tree")
    assert "CRITICAL" in prompt
    assert "markdown code fence" in prompt or "markdown" in prompt
    assert "#!/usr/bin/env bash" in prompt
    assert "set -euo pipefail" in prompt
    # The prompt must explicitly forbid replacing a script by prose
    # (the start.sh / stop.sh / healthcheck.sh failure mode).
    assert "natural-language" in prompt or "description" in prompt
    # And explicitly require deployment.md to remain a real document.
    assert "deployment.md" in prompt


# ── run_scripts ───────────────────────────────────────────────────────────────

import run_scripts  # noqa: E402
from run_scripts import _extract_files  # noqa: E402

_SH_BODY = """\
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
echo "running"
"""

_VALID_SCRIPTS_OUTPUT = (
    f"--- BEGIN FILE: .ai-dev-factory/scripts/bootstrap.sh ---\n{_SH_BODY}--- END FILE ---\n"
    f"--- BEGIN FILE: .ai-dev-factory/scripts/build.sh ---\n{_SH_BODY}--- END FILE ---\n"
    f"--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---\n{_SH_BODY}--- END FILE ---\n"
    f"--- BEGIN FILE: .ai-dev-factory/scripts/stop.sh ---\n{_SH_BODY}--- END FILE ---\n"
    f"--- BEGIN FILE: .ai-dev-factory/scripts/restart.sh ---\n{_SH_BODY}--- END FILE ---\n"
    f"--- BEGIN FILE: .ai-dev-factory/scripts/healthcheck.sh ---\n{_SH_BODY}--- END FILE ---\n"
    "--- BEGIN FILE: .ai-dev-factory/deployment.md ---\n"
    "# Deployment Guide\n\n"
    "## Overview\n"
    "A complete operational document, large enough and structured enough\n"
    "to clear the validator thresholds (300 bytes, >= 2 headings).\n\n"
    "## Scripts\n"
    "- bootstrap.sh — first-time setup\n"
    "- build.sh — build containers\n"
    "- start.sh / stop.sh / restart.sh — lifecycle\n"
    "- healthcheck.sh — liveness probes\n\n"
    "## Environment variables\n"
    "See deploy/.env.example for the full list.\n"
    "--- END FILE ---\n"
)


def test_extract_files_valid_scripts_output():
    result = _extract_files(_VALID_SCRIPTS_OUTPUT)
    assert set(result.keys()) == set(_EXPECTED_FILE_BLOCKS)


def test_extract_files_empty_output():
    assert _extract_files("no blocks here") == {}


def test_extract_files_partial_block():
    partial = "--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---\nno closing"
    assert _extract_files(partial) == {}


def _patch_run_scripts(monkeypatch, tmp_path, llm_output, project_id="testproj"):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(run_scripts, "_invoke_llm", lambda *a, **kw: llm_output)
    monkeypatch.setattr(run_scripts, "_scan_project", lambda p: _MOCK_SCAN)
    monkeypatch.setattr(run_scripts, "_load_deploy_profile_yaml", lambda p: "version: 1\n")
    monkeypatch.setattr(
        run_scripts,
        "commit_and_push",
        lambda *a, **kw: (f"ai-scripts/{project_id}-20260101-120000", "https://github.com/org/repo/pull/99"),
    )
    monkeypatch.setattr(sys, "argv", [
        "run_scripts.py",
        "--project-root", str(tmp_path),
        "--project-id", project_id,
        "--exec-cmd", "claude",
    ])


def test_main_happy_path_writes_scripts_and_state(tmp_path, monkeypatch):
    _patch_run_scripts(monkeypatch, tmp_path, _VALID_SCRIPTS_OUTPUT)

    run_scripts.main()

    for rel in _EXPECTED_FILE_BLOCKS:
        assert (tmp_path / rel).exists(), f"missing {rel}"

    for sh in _EXPECTED_FILE_BLOCKS:
        if sh.endswith(".sh"):
            mode = (tmp_path / sh).stat().st_mode
            assert mode & 0o111, f"{sh} is not executable"

    state = json.loads((tmp_path / "state" / "scripts-testproj.json").read_text())
    assert state["state"] == "success"
    assert state["branch"] == "ai-scripts/testproj-20260101-120000"
    assert state["pr_url"] == "https://github.com/org/repo/pull/99"
    assert state["error"] is None


def test_main_missing_required_file_sets_failed_state(tmp_path, monkeypatch):
    output_missing_stop = _VALID_SCRIPTS_OUTPUT.replace(
        f"--- BEGIN FILE: .ai-dev-factory/scripts/stop.sh ---\n{_SH_BODY}--- END FILE ---\n",
        "",
    )
    _patch_run_scripts(monkeypatch, tmp_path, output_missing_stop, project_id="proj2")

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "scripts-proj2.json").read_text())
    assert state["state"] == "failed"
    assert "stop.sh" in state["error"]


def test_main_path_traversal_rejected(tmp_path, monkeypatch):
    traversal_output = (
        "--- BEGIN FILE: ../../etc/passwd ---\nrooted\n--- END FILE ---\n"
        + _VALID_SCRIPTS_OUTPUT
    )
    _patch_run_scripts(monkeypatch, tmp_path, traversal_output, project_id="proj3")

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "scripts-proj3.json").read_text())
    assert state["state"] == "failed"
    assert "escaping project root" in state["error"]
    assert not (tmp_path / "etc" / "passwd").exists()


def _bad_output_with_markdown_fences() -> str:
    """Reproduces PR #114's bootstrap.sh bug."""
    return _VALID_SCRIPTS_OUTPUT.replace(
        f"--- BEGIN FILE: .ai-dev-factory/scripts/bootstrap.sh ---\n{_SH_BODY}--- END FILE ---",
        "--- BEGIN FILE: .ai-dev-factory/scripts/bootstrap.sh ---\n"
        "```bash\n#!/usr/bin/env bash\nset -euo pipefail\necho bootstrap\n```\n"
        "--- END FILE ---",
    )


def _bad_output_with_prose_script() -> str:
    """Reproduces PR #114's start.sh bug."""
    return _VALID_SCRIPTS_OUTPUT.replace(
        f"--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---\n{_SH_BODY}--- END FILE ---",
        "--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---\n"
        "Starts supervisor then Docker stack then daemon.\n"
        "--- END FILE ---",
    )


def _bad_output_with_summary_deployment_md() -> str:
    """Reproduces PR #114's deployment.md bug."""
    # Replace the (good, multi-section) deployment.md block with a one-liner.
    md_start = _VALID_SCRIPTS_OUTPUT.index(
        "--- BEGIN FILE: .ai-dev-factory/deployment.md ---"
    )
    return _VALID_SCRIPTS_OUTPUT[:md_start] + (
        "--- BEGIN FILE: .ai-dev-factory/deployment.md ---\n"
        "Updated — covers overview, scripts, and env variables.\n"
        "--- END FILE ---\n"
    )


def test_main_rejects_markdown_fences_before_writing_or_committing(tmp_path, monkeypatch):
    """Real PR #114 regression: bootstrap.sh wrapped in ```bash ... ```."""
    commit_calls: list = []
    _patch_run_scripts(monkeypatch, tmp_path, _bad_output_with_markdown_fences(), project_id="badfence")
    monkeypatch.setattr(
        run_scripts,
        "commit_and_push",
        lambda *a, **kw: commit_calls.append(a) or ("br", "url"),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    assert commit_calls == [], "commit_and_push must not run when validation fails"
    assert not (tmp_path / ".ai-dev-factory" / "scripts" / "bootstrap.sh").exists(), \
        "no file may be written when validation fails"
    state = json.loads((tmp_path / "state" / "scripts-badfence.json").read_text())
    assert state["state"] == "failed"
    assert "markdown code fence" in state["error"]
    assert "bootstrap.sh" in state["error"]


def test_main_rejects_prose_script_before_writing_or_committing(tmp_path, monkeypatch):
    commit_calls: list = []
    _patch_run_scripts(monkeypatch, tmp_path, _bad_output_with_prose_script(), project_id="badprose")
    monkeypatch.setattr(
        run_scripts,
        "commit_and_push",
        lambda *a, **kw: commit_calls.append(a) or ("br", "url"),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    assert commit_calls == []
    assert not (tmp_path / ".ai-dev-factory" / "scripts" / "start.sh").exists()
    state = json.loads((tmp_path / "state" / "scripts-badprose.json").read_text())
    assert state["state"] == "failed"
    assert "start.sh" in state["error"]


def test_main_rejects_summary_deployment_md(tmp_path, monkeypatch):
    commit_calls: list = []
    _patch_run_scripts(monkeypatch, tmp_path, _bad_output_with_summary_deployment_md(), project_id="badmd")
    monkeypatch.setattr(
        run_scripts,
        "commit_and_push",
        lambda *a, **kw: commit_calls.append(a) or ("br", "url"),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    assert commit_calls == []
    state = json.loads((tmp_path / "state" / "scripts-badmd.json").read_text())
    assert state["state"] == "failed"
    assert "deployment.md" in state["error"]


def test_main_rejects_empty_llm_output(tmp_path, monkeypatch):
    commit_calls: list = []
    _patch_run_scripts(monkeypatch, tmp_path, "no FILE blocks here", project_id="empty")
    monkeypatch.setattr(
        run_scripts,
        "commit_and_push",
        lambda *a, **kw: commit_calls.append(a) or ("br", "url"),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    assert commit_calls == []
    state = json.loads((tmp_path / "state" / "scripts-empty.json").read_text())
    assert state["state"] == "failed"
    assert "no parseable FILE blocks" in state["error"]


def test_main_logs_validation_aborted_message(tmp_path, monkeypatch, caplog):
    _patch_run_scripts(monkeypatch, tmp_path, _bad_output_with_prose_script(), project_id="logabort")
    monkeypatch.setattr(run_scripts, "commit_and_push", lambda *a, **kw: ("br", "url"))

    caplog.set_level("INFO", logger="run_scripts")
    with pytest.raises(SystemExit):
        run_scripts.main()

    messages = "\n".join(r.message for r in caplog.records)
    assert "validation failed" in messages
    assert "generation aborted before commit" in messages


def test_main_logs_validation_passed_on_clean_output(tmp_path, monkeypatch, caplog):
    _patch_run_scripts(monkeypatch, tmp_path, _VALID_SCRIPTS_OUTPUT, project_id="logok")
    caplog.set_level("INFO", logger="run_scripts")

    run_scripts.main()

    messages = "\n".join(r.message for r in caplog.records)
    assert "validating generated scripts" in messages
    assert "validation passed" in messages


def test_main_llm_failure_sets_failed_state(tmp_path, monkeypatch):
    def _fail_llm(*a, **kw):
        raise RuntimeError("LLM execution failed (exit 1): timeout")

    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(run_scripts, "_invoke_llm", _fail_llm)
    monkeypatch.setattr(run_scripts, "_scan_project", lambda p: _MOCK_SCAN)
    monkeypatch.setattr(run_scripts, "_load_deploy_profile_yaml", lambda p: "")
    monkeypatch.setattr(sys, "argv", [
        "run_scripts.py",
        "--project-root", str(tmp_path),
        "--project-id", "proj4",
        "--exec-cmd", "claude",
    ])

    with pytest.raises(SystemExit) as exc_info:
        run_scripts.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "scripts-proj4.json").read_text())
    assert state["state"] == "failed"
    assert "LLM" in state["error"]


# ── scripts_git_service ───────────────────────────────────────────────────────

from scripts_git_service import commit_and_push  # noqa: E402

_PR_URL = "https://github.com/org/repo/pull/99"


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


def test_scripts_branch_name_format(tmp_path, monkeypatch):
    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list) and "list" in cmd:
            return _completed(stdout="[]")
        if isinstance(cmd, list) and "create" in cmd:
            return _completed(stdout=_PR_URL)
        return _completed()

    monkeypatch.setattr("scripts_git_service.subprocess.run", mock_run)

    branch, _ = commit_and_push(tmp_path, "proj1")

    assert re.match(r"^ai-scripts/proj1-\d{8}-\d{6}$", branch), f"unexpected branch: {branch!r}"


def test_scripts_pr_created_on_new_branch(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list):
            calls.append(cmd)
            if "list" in cmd:
                return _completed(stdout="[]")
            if "create" in cmd:
                return _completed(stdout=_PR_URL)
        return _completed()

    monkeypatch.setattr("scripts_git_service.subprocess.run", mock_run)

    branch, pr_url = commit_and_push(tmp_path, "proj1")

    create_calls = [c for c in calls if isinstance(c, list) and "create" in c]
    assert create_calls, "gh pr create was not called"
    assert pr_url == _PR_URL


def test_scripts_pr_updated_on_existing_branch(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list):
            calls.append(cmd)
            if "list" in cmd:
                return _completed(stdout=json.dumps([{"url": _PR_URL}]))
            if "edit" in cmd:
                return _completed()
        return _completed()

    monkeypatch.setattr("scripts_git_service.subprocess.run", mock_run)

    branch, pr_url = commit_and_push(tmp_path, "proj1")

    edit_calls = [c for c in calls if isinstance(c, list) and "edit" in c]
    create_calls = [c for c in calls if isinstance(c, list) and "create" in c]
    assert edit_calls, "gh pr edit was not called"
    assert not create_calls, "gh pr create should not be called when PR already exists"
    assert pr_url == _PR_URL


def test_scripts_git_stages_scripts_dir(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list):
            calls.append(cmd)
            if "list" in cmd:
                return _completed(stdout="[]")
            if "create" in cmd:
                return _completed(stdout=_PR_URL)
        return _completed()

    monkeypatch.setattr("scripts_git_service.subprocess.run", mock_run)

    commit_and_push(tmp_path, "proj1")

    add_calls = [c for c in calls if isinstance(c, list) and c[:2] == ["git", "add"]]
    assert add_calls, "git add was not called"
    staged_paths = [item for call in add_calls for item in call[2:]]
    assert any("scripts" in p for p in staged_paths), "scripts/ dir not staged"
    assert any("deployment.md" in p for p in staged_paths), "deployment.md not staged"


# ── scripts_manager ───────────────────────────────────────────────────────────

from services.control_api.services import scripts_manager  # noqa: E402

_SUP = "http://localhost:8090"


class _MockResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def test_start_scripts_delegates_to_supervisor(monkeypatch):
    calls = []

    def mock_post(url, **kwargs):
        calls.append(url)
        return _MockResponse(200, {"ok": True})

    monkeypatch.setattr(scripts_manager.httpx, "post", mock_post)

    result = scripts_manager.start_scripts("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is True
    assert any("/scripts/start" in u for u in calls)


def test_start_scripts_supervisor_unreachable(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(scripts_manager.httpx, "post", mock_post)

    result = scripts_manager.start_scripts("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is False
    assert result.error == "supervisor_unreachable"


def test_start_scripts_returns_409_when_locked(monkeypatch):
    monkeypatch.setattr(
        scripts_manager.httpx,
        "post",
        lambda *a, **kw: _MockResponse(409, {"error": "locked"}),
    )

    result = scripts_manager.start_scripts("proj1", "/path/proj", "claude", _SUP)

    assert result.ok is False
    assert result.error == "locked"


def test_start_scripts_no_supervisor_url():
    result = scripts_manager.start_scripts("proj1", "/path/proj", "claude", None)

    assert result.ok is False
    assert result.error == "no_supervisor_url"


def test_get_scripts_status_proxies_supervisor_response(monkeypatch):
    payload = {
        "state": "success",
        "started_at": "2026-01-01T00:00:00",
        "finished_at": "2026-01-01T00:05:00",
        "error": None,
        "branch": "ai-scripts/proj1-20260101-120000",
        "pr_url": _PR_URL,
    }

    monkeypatch.setattr(
        scripts_manager.httpx,
        "get",
        lambda *a, **kw: _MockResponse(200, payload),
    )

    status = scripts_manager.get_scripts_status("proj1", _SUP)

    assert status.state == "success"
    assert status.branch == "ai-scripts/proj1-20260101-120000"
    assert status.pr_url == _PR_URL


# ── deployer routes ───────────────────────────────────────────────────────────

def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / ".git").mkdir()
    return create_app(project_root=proj, projects_root=tmp_path), proj


def test_generate_scripts_returns_503_when_no_supervisor(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/generate-scripts")
    assert r.status_code == 503


def test_get_scripts_status_returns_idle_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/myproject/deployer/scripts/status")
    assert r.status_code == 200
    assert r.json()["state"] == "idle"


def test_get_scripts_logs_returns_empty_when_no_supervisor(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/myproject/deployer/scripts/logs")
    assert r.status_code == 200
    assert r.json()["lines"] == []


def test_scripts_endpoints_return_404_for_unknown_project(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_SUPERVISOR_URL", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)

    assert client.post("/projects/no-such/deployer/generate-scripts").status_code == 404
    assert client.get("/projects/no-such/deployer/scripts/status").status_code == 404
    assert client.get("/projects/no-such/deployer/scripts/logs").status_code == 404
