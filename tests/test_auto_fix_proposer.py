"""Tests for services/supervisor/auto_fix_proposer.py

Cases covered:
1. collect_failure_context — reads deploy.yml
2. collect_failure_context — reads sandbox state and logs
3. collect_failure_context — reads operational scripts generically (no name assumptions)
4. call_ai_runtime — parses valid JSON array from AI output
5. call_ai_runtime — raises ValueError on malformed (non-array) AI output
6. validate_patches — marks in-scope paths as valid
7. validate_patches — rejects path traversal and out-of-scope paths
8. persist_proposal / load_proposal / list_proposals — round-trip persistence
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

import auto_fix_proposer as afp  # noqa: E402


# ── 1. collect_failure_context reads deploy.yml ───────────────────────────────

def test_collect_reads_deploy_yml(tmp_path):
    scripts_dir = tmp_path / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    deploy = tmp_path / ".ai-dev-factory" / "deploy.yml"
    deploy.write_text("version: 1\nproject: test\n")

    rt = tmp_path / "runtime"
    ctx = afp.collect_failure_context("sid1", tmp_path, runtime_root=rt)

    assert ctx["deploy_profile"] == "version: 1\nproject: test\n"


# ── 2. collect reads sandbox state and logs ───────────────────────────────────

def test_collect_reads_sandbox_state_and_logs(tmp_path):
    rt = tmp_path / "runtime"
    sandbox_dir = rt / "sandboxes" / "sid2"
    sandbox_dir.mkdir(parents=True)
    state = {"state": "failed", "last_step": "build.sh"}
    (sandbox_dir / "state.json").write_text(json.dumps(state))
    (sandbox_dir / "run.log").write_text("line1\nline2\nline3\n")

    ctx = afp.collect_failure_context("sid2", tmp_path, runtime_root=rt)

    assert ctx["sandbox_state"] == state
    assert ctx["logs"] == ["line1", "line2", "line3"]


# ── 3. collect reads scripts generically ──────────────────────────────────────

def test_collect_reads_scripts_without_name_assumptions(tmp_path):
    scripts_dir = tmp_path / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "start.sh").write_text("#!/bin/sh\necho start\n")
    (scripts_dir / "custom_check.sh").write_text("#!/bin/sh\necho check\n")

    ctx = afp.collect_failure_context("sid3", tmp_path, runtime_root=tmp_path / "rt")

    assert "start.sh" in ctx["operational_scripts"]
    assert "custom_check.sh" in ctx["operational_scripts"]
    assert ctx["operational_scripts"]["start.sh"] == "#!/bin/sh\necho start\n"


# ── 4. call_ai_runtime parses valid JSON array ────────────────────────────────

def test_call_ai_runtime_parses_json_array(tmp_path, monkeypatch):
    ai_output = json.dumps([
        {
            "relative_path": ".ai-dev-factory/scripts/start.sh",
            "content": "#!/bin/sh\necho fixed\n",
            "reasoning": "fixed the start script",
        }
    ])

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=ai_output, stderr="")

    monkeypatch.setattr(afp.subprocess, "run", fake_run)

    patches = afp.call_ai_runtime({}, "echo", tmp_path)

    assert len(patches) == 1
    assert patches[0]["relative_path"] == ".ai-dev-factory/scripts/start.sh"


# ── 5. call_ai_runtime raises ValueError on malformed output ──────────────────

def test_call_ai_runtime_raises_on_malformed_output(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="no json here", stderr="")

    monkeypatch.setattr(afp.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="JSON array"):
        afp.call_ai_runtime({}, "echo", tmp_path)


# ── 6. validate_patches marks in-scope paths as valid ────────────────────────

def test_validate_patches_allows_scripts_dir(tmp_path):
    patches = [
        {"relative_path": ".ai-dev-factory/scripts/start.sh", "content": "#!/bin/sh\n"},
        {"relative_path": ".ai-dev-factory/scripts/build.sh", "content": "#!/bin/sh\n"},
    ]
    validated = afp.validate_patches(patches, tmp_path)

    assert all(p["valid"] for p in validated)
    assert validated[0]["relative_path"] == ".ai-dev-factory/scripts/start.sh"


# ── 7. validate_patches rejects traversal and out-of-scope paths ──────────────

@pytest.mark.parametrize("bad_path", [
    "../../etc/passwd",
    ".ai-dev-factory/env",
    "Dockerfile",
    "/etc/hosts",
    ".ai-dev-factory/scripts/../env",
    "",
])
def test_validate_patches_rejects_disallowed_paths(tmp_path, bad_path):
    patches = [{"relative_path": bad_path, "content": "x"}]
    validated = afp.validate_patches(patches, tmp_path)
    assert validated[0]["valid"] is False, f"expected rejection for: {bad_path!r}"


# ── 8. persist / load / list round-trip ──────────────────────────────────────

def test_persist_load_list_proposals(tmp_path):
    rt = tmp_path / "runtime"

    p1 = afp.make_proposal("abc123", "proj1", "sb1", "build.sh")
    p1["status"] = "ready"
    afp.persist_proposal("proj1", p1, rt)

    p2 = afp.make_proposal("def456", "proj1", "sb2", "start.sh")
    p2["status"] = "error"
    p2["error"] = "timeout"
    afp.persist_proposal("proj1", p2, rt)

    loaded = afp.load_proposal("proj1", "abc123", rt)
    assert loaded is not None
    assert loaded["status"] == "ready"
    assert loaded["sandbox_id"] == "sb1"

    missing = afp.load_proposal("proj1", "notexist", rt)
    assert missing is None

    all_proposals = afp.list_proposals("proj1", rt)
    assert len(all_proposals) == 2
    ids = [p["proposal_id"] for p in all_proposals]
    assert "abc123" in ids
    assert "def456" in ids
