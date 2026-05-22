"""Tests for services/supervisor/auto_fix_loop.py

Cases covered:
1. apply_patches — writes valid patches, skips invalid, returns changed paths
2. run_scripts_validation — success when all scripts exit 0
3. run_scripts_validation — fails when a script exits non-zero
4. run_scripts_validation — fails on missing required script
5. run_auto_fix_loop — successful convergence after one failing iteration
6. run_auto_fix_loop — retry limit reached (all iterations fail)
7. run_auto_fix_loop — malformed AI output counted as error iteration, loop continues
8. run_auto_fix_loop — patch application failure counted as error iteration
9. iteration history persistence — session + iterations survive on disk
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

import auto_fix_loop as afl  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_scripts(project_root: Path, exit_code: int = 0) -> None:
    scripts_dir = project_root / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in afl._REQUIRED_SCRIPTS:
        script = scripts_dir / name
        script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
        script.chmod(0o755)


def _make_runtime(tmp_path: Path) -> Path:
    rt = tmp_path / "runtime"
    rt.mkdir()
    return rt


# ── 1. apply_patches ──────────────────────────────────────────────────────────

def test_apply_patches_writes_valid_and_skips_invalid(tmp_path):
    scripts_dir = tmp_path / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    patches = [
        {"relative_path": ".ai-dev-factory/scripts/start.sh", "content": "#!/bin/sh\nexit 0\n", "valid": True},
        {"relative_path": "Dockerfile", "content": "FROM ubuntu", "valid": False},
    ]
    changed = afl.apply_patches(patches, tmp_path)

    assert changed == [".ai-dev-factory/scripts/start.sh"]
    assert (tmp_path / ".ai-dev-factory" / "scripts" / "start.sh").read_text() == "#!/bin/sh\nexit 0\n"
    assert not (tmp_path / "Dockerfile").exists()


# ── 2. run_scripts_validation success ────────────────────────────────────────

def test_run_scripts_validation_success(tmp_path):
    _make_scripts(tmp_path, exit_code=0)
    iter_dir = tmp_path / "iter-1"
    iter_dir.mkdir()

    success, error, steps = afl.run_scripts_validation(tmp_path, iter_dir)

    assert success is True
    assert error is None
    assert len(steps) == len(afl._REQUIRED_SCRIPTS)
    assert all(s["status"] == "success" for s in steps)


# ── 3. run_scripts_validation fail on non-zero exit ──────────────────────────

def test_run_scripts_validation_fails_on_nonzero(tmp_path):
    _make_scripts(tmp_path, exit_code=0)
    # Make bootstrap.sh fail
    (tmp_path / ".ai-dev-factory" / "scripts" / "bootstrap.sh").write_text(
        "#!/bin/sh\nexit 1\n"
    )
    iter_dir = tmp_path / "iter-1"
    iter_dir.mkdir()

    success, error, steps = afl.run_scripts_validation(tmp_path, iter_dir)

    assert success is False
    assert "bootstrap.sh" in error
    assert steps[0]["status"] == "failed"


# ── 4. run_scripts_validation fails on missing script ────────────────────────

def test_run_scripts_validation_fails_on_missing_script(tmp_path):
    # Only create some scripts, not all
    scripts_dir = tmp_path / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    iter_dir = tmp_path / "iter-1"
    iter_dir.mkdir()

    success, error, steps = afl.run_scripts_validation(tmp_path, iter_dir)

    assert success is False
    assert "missing" in error
    assert steps[0]["status"] == "failed"


# ── 5. run_auto_fix_loop — convergence after one fix ─────────────────────────

def test_loop_converges_after_one_fix(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    rt = _make_runtime(tmp_path)

    # Deploy context
    scripts_dir = project_root / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    for name in afl._REQUIRED_SCRIPTS:
        (scripts_dir / name).write_text(f"#!/bin/sh\nexit 0\n")

    call_count = {"n": 0}

    def fake_collect(sandbox_id, project_root_, runtime_root=None):
        return {"deploy_profile": "", "sandbox_state": {}, "logs": [], "operational_scripts": {}}

    def fake_call_ai(context, exec_cmd, project_root_, failing_step=None):
        call_count["n"] += 1
        return [{
            "relative_path": ".ai-dev-factory/scripts/start.sh",
            "content": "#!/bin/sh\nexit 0\n",
            "reasoning": "fixed",
        }]

    session = afl.make_session("proj1", "sb1", max_retries=3)

    with patch.object(afl, "collect_failure_context", fake_collect), \
         patch.object(afl, "call_ai_runtime", fake_call_ai), \
         patch.object(afl, "run_scripts_validation", return_value=(True, None, [])):
        afl.run_auto_fix_loop(session, project_root, "echo", rt)

    assert session["status"] == "success"
    assert session["current_iteration"] == 1
    assert len(session["iterations"]) == 1
    assert session["iterations"][0]["status"] == "success"
    assert ".ai-dev-factory/scripts/start.sh" in session["iterations"][0]["changed_files"]


# ── 6. run_auto_fix_loop — retry limit reached ────────────────────────────────

def test_loop_fails_when_max_retries_reached(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    rt = _make_runtime(tmp_path)
    (project_root / ".ai-dev-factory" / "scripts").mkdir(parents=True)

    def fake_collect(*a, **kw):
        return {"deploy_profile": "", "sandbox_state": {}, "logs": [], "operational_scripts": {}}

    def fake_call_ai(context, exec_cmd, project_root_, failing_step=None):
        return [{
            "relative_path": ".ai-dev-factory/scripts/start.sh",
            "content": "#!/bin/sh\nexit 1\n",
            "reasoning": "attempt",
        }]

    session = afl.make_session("proj1", "sb1", max_retries=2)

    with patch.object(afl, "collect_failure_context", fake_collect), \
         patch.object(afl, "call_ai_runtime", fake_call_ai), \
         patch.object(afl, "run_scripts_validation", return_value=(False, "build failed", [{"name": "build.sh", "status": "failed"}])):
        afl.run_auto_fix_loop(session, project_root, "echo", rt)

    assert session["status"] == "failed"
    assert len(session["iterations"]) == 2
    assert all(it["status"] == "failed" for it in session["iterations"])


# ── 7. malformed AI output counted as error iteration ────────────────────────

def test_loop_handles_malformed_ai_output(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    rt = _make_runtime(tmp_path)
    (project_root / ".ai-dev-factory" / "scripts").mkdir(parents=True)

    def fake_collect(*a, **kw):
        return {"deploy_profile": "", "sandbox_state": {}, "logs": [], "operational_scripts": {}}

    def fake_call_ai_bad(context, exec_cmd, project_root_, failing_step=None):
        raise ValueError("AI output did not contain a JSON array")

    session = afl.make_session("proj1", "sb1", max_retries=2)

    with patch.object(afl, "collect_failure_context", fake_collect), \
         patch.object(afl, "call_ai_runtime", fake_call_ai_bad):
        afl.run_auto_fix_loop(session, project_root, "echo", rt)

    assert session["status"] == "failed"
    assert all(it["status"] == "error" for it in session["iterations"])
    assert all("AI runtime error" in (it["error"] or "") for it in session["iterations"])


# ── 8. patch application failure counted as error iteration ──────────────────

def test_loop_handles_patch_application_failure(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    rt = _make_runtime(tmp_path)
    (project_root / ".ai-dev-factory" / "scripts").mkdir(parents=True)

    def fake_collect(*a, **kw):
        return {"deploy_profile": "", "sandbox_state": {}, "logs": [], "operational_scripts": {}}

    def fake_call_ai(context, exec_cmd, project_root_, failing_step=None):
        return [{
            "relative_path": ".ai-dev-factory/scripts/start.sh",
            "content": "#!/bin/sh\nexit 0\n",
            "reasoning": "fix",
        }]

    session = afl.make_session("proj1", "sb1", max_retries=1)

    with patch.object(afl, "collect_failure_context", fake_collect), \
         patch.object(afl, "call_ai_runtime", fake_call_ai), \
         patch.object(afl, "apply_patches", side_effect=OSError("disk full")):
        afl.run_auto_fix_loop(session, project_root, "echo", rt)

    assert session["status"] == "failed"
    assert session["iterations"][0]["status"] == "error"
    assert "patch application failed" in session["iterations"][0]["error"]


# ── 9. iteration history persistence ─────────────────────────────────────────

def test_loop_iteration_history_persisted(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    rt = _make_runtime(tmp_path)
    (project_root / ".ai-dev-factory" / "scripts").mkdir(parents=True)

    def fake_collect(*a, **kw):
        return {"deploy_profile": "", "sandbox_state": {}, "logs": [], "operational_scripts": {}}

    def fake_call_ai(context, exec_cmd, project_root_, failing_step=None):
        return [{
            "relative_path": ".ai-dev-factory/scripts/start.sh",
            "content": "#!/bin/sh\nexit 0\n",
            "reasoning": "fixed",
        }]

    session = afl.make_session("proj2", "sb2", max_retries=3)

    with patch.object(afl, "collect_failure_context", fake_collect), \
         patch.object(afl, "call_ai_runtime", fake_call_ai), \
         patch.object(afl, "run_scripts_validation", return_value=(True, None, [])):
        afl.run_auto_fix_loop(session, project_root, "echo", rt)

    # Load from disk and verify
    loaded = afl.load_session("proj2", session["session_id"], rt)
    assert loaded is not None
    assert loaded["status"] == "success"
    assert len(loaded["iterations"]) == 1
    assert loaded["iterations"][0]["changed_files"] == [".ai-dev-factory/scripts/start.sh"]

    # list_sessions also returns it
    all_sessions = afl.list_sessions("proj2", rt)
    assert any(s["session_id"] == session["session_id"] for s in all_sessions)
