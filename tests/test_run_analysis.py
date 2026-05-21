"""Tests for run_analysis — _extract_files(), file generation, and main() orchestration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_analysis
from run_analysis import _extract_files

_VALID_OUTPUT = """\
--- BEGIN FILE: .ai-dev-factory/deploy.yml ---
version: "1"
components: []
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment Guide
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/runtime-notes.md ---
# Notes
--- END FILE ---
"""

_MOCK_SCAN = {
    "docker_services": [],
    "python_backend": False,
    "node_frontend": False,
    "required_tools": [],
}


# --- _extract_files ---

def test_extract_files_valid_response():
    result = _extract_files(_VALID_OUTPUT)
    assert set(result.keys()) == {
        ".ai-dev-factory/deploy.yml",
        ".ai-dev-factory/deployment.md",
        ".ai-dev-factory/runtime-notes.md",
    }
    assert 'version: "1"' in result[".ai-dev-factory/deploy.yml"]


def test_extract_files_empty_output():
    assert _extract_files("no blocks here") == {}


def test_extract_files_malformed_delimiter():
    malformed = "--- BEGIN FILE .ai-dev-factory/deploy.yml ---\ncontent\n--- END FILE ---"
    assert _extract_files(malformed) == {}


def test_extract_files_partial_block():
    partial = "--- BEGIN FILE: .ai-dev-factory/deploy.yml ---\nno closing delimiter"
    assert _extract_files(partial) == {}


# --- main() orchestration ---

def _patch_main(monkeypatch, tmp_path, llm_output, project_id="testproj"):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(run_analysis, "_invoke_llm", lambda *a, **kw: llm_output)
    monkeypatch.setattr(run_analysis, "_scan_project", lambda p: _MOCK_SCAN)
    monkeypatch.setattr(
        run_analysis,
        "commit_and_push",
        lambda *a, **kw: ("ai-analysis/testproj-20260101-120000", "https://github.com/org/repo/pull/42"),
    )
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--project-root", str(tmp_path),
        "--project-id", project_id,
        "--exec-cmd", "claude",
    ])


def test_main_happy_path_writes_files_and_state(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path, _VALID_OUTPUT)

    run_analysis.main()

    assert (tmp_path / ".ai-dev-factory" / "deploy.yml").exists()
    assert (tmp_path / ".ai-dev-factory" / "deployment.md").exists()

    state = json.loads((tmp_path / "state" / "analysis-testproj.json").read_text())
    assert state["state"] == "success"
    assert state["branch"] == "ai-analysis/testproj-20260101-120000"
    assert state["pr_url"] == "https://github.com/org/repo/pull/42"
    assert state["error"] is None


def test_main_missing_required_file_sets_failed_state(tmp_path, monkeypatch):
    output_without_deploy = """\
--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment Guide
--- END FILE ---
"""
    _patch_main(monkeypatch, tmp_path, output_without_deploy, project_id="proj2")

    with pytest.raises(SystemExit) as exc_info:
        run_analysis.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "analysis-proj2.json").read_text())
    assert state["state"] == "failed"
    assert "deploy.yml" in state["error"]


def test_main_path_traversal_rejected(tmp_path, monkeypatch):
    traversal_output = """\
--- BEGIN FILE: ../../etc/passwd ---
rooted
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deploy.yml ---
version: "1"
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment
--- END FILE ---
"""
    _patch_main(monkeypatch, tmp_path, traversal_output, project_id="proj3")

    with pytest.raises(SystemExit) as exc_info:
        run_analysis.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "analysis-proj3.json").read_text())
    assert state["state"] == "failed"
    assert "escaping project root" in state["error"]
    assert not (tmp_path / "etc" / "passwd").exists()


def test_main_path_traversal_with_prefix_bypass_rejected(tmp_path, monkeypatch):
    """Path starting with .ai-dev-factory/ but using .. to escape is rejected after resolve."""
    traversal_output = """\
--- BEGIN FILE: .ai-dev-factory/../../../etc/passwd ---
rooted
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deploy.yml ---
version: "1"
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment
--- END FILE ---
"""
    _patch_main(monkeypatch, tmp_path, traversal_output, project_id="proj5")

    with pytest.raises(SystemExit) as exc_info:
        run_analysis.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "analysis-proj5.json").read_text())
    assert state["state"] == "failed"
    assert "escaping project root" in state["error"]


def test_main_llm_failure_sets_failed_state(tmp_path, monkeypatch):
    def _fail_llm(*a, **kw):
        raise RuntimeError("LLM execution failed (exit 1): timeout")

    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(run_analysis, "_invoke_llm", _fail_llm)
    monkeypatch.setattr(run_analysis, "_scan_project", lambda p: _MOCK_SCAN)
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--project-root", str(tmp_path),
        "--project-id", "proj4",
        "--exec-cmd", "claude",
    ])

    with pytest.raises(SystemExit) as exc_info:
        run_analysis.main()

    assert exc_info.value.code == 1
    state = json.loads((tmp_path / "state" / "analysis-proj4.json").read_text())
    assert state["state"] == "failed"
    assert "LLM" in state["error"]
