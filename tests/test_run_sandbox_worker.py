"""Tests for the host-side sandbox-validation worker.

This file used to drive the in-container ``sandbox_runner`` via the
control-api TestClient. The worker has since moved to
``tools/agent_runner/run_sandbox.py`` (executed host-side by the
supervisor), so tests now exercise the worker module directly. The
robustness invariants from PR #120 are preserved verbatim — none of
them depended on the HTTP layer.
"""

from __future__ import annotations

import json
import subprocess as _subprocess
import sys
from pathlib import Path

import pytest

# Import the worker as a flat module — same trick the supervisor uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_sandbox  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_git_project(tmp_path: Path) -> Path:
    proj = tmp_path / "myproject"
    proj.mkdir()
    _subprocess.run(["git", "init", str(proj)], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(proj), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    (proj / "README.md").write_text("test")
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "commit", "-m", "init"],
        check=True, capture_output=True,
    )
    return proj


_SCRIPTS_REL = ".ai-dev-factory/scripts"


def _add_scripts(proj: Path, scripts: dict[str, str]) -> None:
    """Mirror the generator layout: ``.ai-dev-factory/scripts/<name>``."""
    scripts_dir = proj / _SCRIPTS_REL
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name, content in scripts.items():
        script = scripts_dir / name
        script.write_text(f"#!/bin/bash\n{content}\n")
        script.chmod(0o755)
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "commit", "-m", "add scripts"],
        check=True, capture_output=True,
    )


def _required_scripts_all_ok() -> dict[str, str]:
    return {name: "exit 0" for name in run_sandbox._REQUIRED_SCRIPTS}


_TEST_PROJECT_NAME = "testproject"


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path, monkeypatch):
    """Pin the host runtime root and sandbox root to tmp dirs so tests are hermetic."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", _TEST_PROJECT_NAME)
    return tmp_path / "runtime"


def _sandbox_dir(tmp_path: Path, sandbox_id: str) -> Path:
    return tmp_path / "sandboxes" / _TEST_PROJECT_NAME / sandbox_id


def _read_latest_state(tmp_path: Path, project_id: str = "myproject") -> dict:
    p = tmp_path / "runtime" / "state" / f"sandbox-{project_id}.json"
    return json.loads(p.read_text())


def _read_latest_log(tmp_path: Path, project_id: str = "myproject") -> str:
    base = tmp_path / "sandboxes" / _TEST_PROJECT_NAME
    dirs = [d for d in base.iterdir() if d.is_dir() and d.name.startswith(project_id)]
    assert dirs, f"no sandbox directory found under {base}"
    return (dirs[0] / "run.log").read_text()


def _assert_terminal_failed(state: dict) -> None:
    assert state["state"] == "failed", f"state stuck at {state['state']}"
    assert state["finished_at"] is not None, "finished_at must be set on failure"
    assert state["error"], "error must not be empty on failure"


# ── Happy paths ───────────────────────────────────────────────────────────────


def test_worker_creates_worktree(tmp_path):
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-T1")

    # Project has no scripts → must fail (no more silent success).
    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"
    wt = _sandbox_dir(tmp_path, "myproject-T1") / "worktree"
    assert wt.exists(), "worktree directory must be created before failing"


def test_worker_full_success(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())
    run_sandbox._do_sandbox("myproject", proj, "myproject-OK")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "validated"
    success_steps = [s for s in state["steps"] if s["status"] == "success"]
    assert len(success_steps) == 4
    # All four required scripts must appear in order.
    assert [s["name"] for s in state["steps"]] == run_sandbox._REQUIRED_SCRIPTS


def test_worker_healthcheck_failure(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 0",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 1",
    })
    run_sandbox._do_sandbox("myproject", proj, "myproject-HC")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"
    assert state["last_step"] == "healthcheck.sh"
    assert "healthcheck.sh" in (state.get("error") or "")
    failed = [s for s in state["steps"] if s["status"] == "failed"]
    assert len(failed) == 1


def test_worker_mid_pipeline_failure_skips_later_scripts(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 1",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    run_sandbox._do_sandbox("myproject", proj, "myproject-MID")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"
    by_name = {s["name"]: s for s in state["steps"]}
    assert by_name["bootstrap.sh"]["status"] == "success"
    assert by_name["build.sh"]["status"] == "failed"
    assert "start.sh" not in by_name
    assert "healthcheck.sh" not in by_name


def test_worker_writes_step_output_to_log(tmp_path):
    proj = _make_git_project(tmp_path)
    scripts = _required_scripts_all_ok()
    scripts["bootstrap.sh"] = "echo hello_from_bootstrap"
    _add_scripts(proj, scripts)
    run_sandbox._do_sandbox("myproject", proj, "myproject-LOG")

    log = _read_latest_log(tmp_path)
    assert "hello_from_bootstrap" in log
    # Log must mention both the script name AND the resolved relative path.
    assert "--- bootstrap.sh (.ai-dev-factory/scripts/bootstrap.sh) ---" in log


def test_worker_latest_state_mirrors_per_run_state(tmp_path):
    """The supervisor reads ``state/sandbox-{project_id}.json`` while the
    per-run history lives under ``sandboxes/{id}/state.json``. Both must
    carry the same content after the worker finishes."""
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())
    run_sandbox._do_sandbox("myproject", proj, "myproject-MIRROR")

    latest = json.loads(
        (tmp_path / "runtime" / "state" / "sandbox-myproject.json").read_text()
    )
    per_run = json.loads(
        (_sandbox_dir(tmp_path, "myproject-MIRROR") / "state.json").read_text()
    )
    assert latest == per_run


# ── Compose project name normalisation ───────────────────────────────────────


def _read_deploy_env(tmp_path: Path, sandbox_id: str) -> dict[str, str]:
    env_path = _sandbox_dir(tmp_path, sandbox_id) / "deploy.env"
    out: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        if "=" in line and line.strip():
            k, v = line.split("=", 1)
            out[k] = v
    return out


def test_compose_project_name_is_normalised_in_state(tmp_path):
    """Regression for the production failure:

        invalid project name "sandbox-ai-dev-factory-20260522T204456"

    The sandbox_id contains a UTC timestamp with an uppercase ``T``.
    The persisted ``compose_project`` MUST be lowercase, never the raw
    ``sandbox-<id>`` form.
    """
    proj = _make_git_project(tmp_path)
    raw_sandbox_id = "ai-dev-factory-20260522T204456"
    run_sandbox._do_sandbox("ai-dev-factory", proj, raw_sandbox_id)

    state = _read_latest_state(tmp_path, project_id="ai-dev-factory")
    compose_project = state["compose_project"]

    import re
    assert re.match(r"^[a-z0-9][a-z0-9_-]*$", compose_project), (
        f"compose_project {compose_project!r} is not Compose-valid"
    )
    assert "T" not in compose_project, "uppercase T must be lowered"
    assert compose_project == "sandbox-ai-dev-factory-20260522t204456"


def test_compose_project_name_is_normalised_in_deploy_env(tmp_path):
    """The COMPOSE_PROJECT_NAME env var the generated scripts read MUST
    carry the normalised name — otherwise scripts would re-introduce
    the broken value the moment they call ``docker compose``."""
    proj = _make_git_project(tmp_path)
    raw_sandbox_id = "ai-dev-factory-20260522T204456"
    run_sandbox._do_sandbox("ai-dev-factory", proj, raw_sandbox_id)

    env = _read_deploy_env(tmp_path, raw_sandbox_id)
    assert env["COMPOSE_PROJECT_NAME"] == "sandbox-ai-dev-factory-20260522t204456"
    assert "T" not in env["COMPOSE_PROJECT_NAME"]
    # SANDBOX_ID is informational only and may keep the raw form.
    assert env["SANDBOX_ID"] == raw_sandbox_id


def test_compose_project_name_logged_with_normalisation_note(tmp_path):
    """When normalisation actually changes the name, the log must say so
    — that's the only way a developer can tell from logs alone that the
    pipeline self-healed instead of silently ignoring the issue."""
    proj = _make_git_project(tmp_path)
    raw_sandbox_id = "ai-dev-factory-20260522T204456"
    run_sandbox._do_sandbox("ai-dev-factory", proj, raw_sandbox_id)

    log = _read_latest_log(tmp_path, project_id="ai-dev-factory")
    assert "compose_project: sandbox-ai-dev-factory-20260522t204456" in log
    assert "normalised from 'sandbox-ai-dev-factory-20260522T204456'" in log


def test_already_valid_compose_name_is_not_annotated(tmp_path):
    """If the sandbox_id is already lowercase alphanumeric, the log
    must NOT show a misleading 'normalised from …' note."""
    proj = _make_git_project(tmp_path)
    sid = "myproject-cleanid"
    run_sandbox._do_sandbox("myproject", proj, sid)

    log = _read_latest_log(tmp_path)
    assert "compose_project: sandbox-myproject-cleanid" in log
    assert "normalised from" not in log


# ── Script lookup + missing-script policy ─────────────────────────────────────


def test_scripts_resolved_under_ai_dev_factory_dir(tmp_path):
    """Scripts at the worktree root are NOT picked up — the canonical
    location is `.ai-dev-factory/scripts/`. This guards against a
    silent regression where the runner falls back to the root.
    """
    proj = _make_git_project(tmp_path)
    # Plant a happy-path bootstrap.sh at the WRONG location (root).
    decoy = proj / "bootstrap.sh"
    decoy.write_text("#!/bin/bash\nexit 0\n")
    decoy.chmod(0o755)
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "commit", "-m", "decoy"],
        check=True, capture_output=True,
    )

    run_sandbox._do_sandbox("myproject", proj, "myproject-DECOY")
    state = _read_latest_state(tmp_path)

    assert state["state"] == "failed"
    assert ".ai-dev-factory/scripts/bootstrap.sh" in state["error"]


def test_missing_required_script_fails_validation(tmp_path):
    """Empty `.ai-dev-factory/scripts/` ⇒ validation MUST fail. This is
    the regression the user observed (sandbox reporting "success" with
    every step skipped)."""
    proj = _make_git_project(tmp_path)

    run_sandbox._do_sandbox("myproject", proj, "myproject-EMPTY")
    state = _read_latest_state(tmp_path)

    assert state["state"] == "failed", (
        "missing scripts must fail validation, not silently succeed"
    )
    assert state["error"], "error must explain what is missing"
    assert "required script missing" in state["error"]
    assert ".ai-dev-factory/scripts/bootstrap.sh" in state["error"]


def test_partial_scripts_set_fails_at_first_missing(tmp_path):
    """If `bootstrap.sh` runs but `build.sh` is missing, the run must
    fail at build.sh and report it — not skip and call it a day."""
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {"bootstrap.sh": "exit 0"})

    run_sandbox._do_sandbox("myproject", proj, "myproject-PARTIAL")
    state = _read_latest_state(tmp_path)

    assert state["state"] == "failed"
    assert ".ai-dev-factory/scripts/build.sh" in state["error"]
    by_name = {s["name"]: s for s in state["steps"]}
    assert by_name["bootstrap.sh"]["status"] == "success"
    assert by_name["build.sh"]["status"] == "failed"


def test_log_records_resolved_script_paths(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())
    run_sandbox._do_sandbox("myproject", proj, "myproject-LOGS")

    log = _read_latest_log(tmp_path)
    # Scripts dir + each fully-resolved path must appear at least once.
    assert "scripts dir (relative): .ai-dev-factory/scripts" in log
    assert "scripts dir (absolute): " in log
    for name in run_sandbox._REQUIRED_SCRIPTS:
        assert f".ai-dev-factory/scripts/{name}" in log


def test_log_explains_missing_script_clearly(tmp_path):
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-MISSING-LOG")

    log = _read_latest_log(tmp_path)
    assert "required script missing: .ai-dev-factory/scripts/bootstrap.sh" in log


def test_scripts_executed_with_worktree_as_cwd(tmp_path):
    """Generated scripts assume they run from the project root, so that
    relative paths (`npm install`, `docker compose up`) work. The worker
    must use ``cwd=<worktree>``, not ``cwd=<scripts_dir>``."""
    proj = _make_git_project(tmp_path)
    # bootstrap echoes its own pwd; if cwd is the scripts dir the test
    # fails immediately.
    scripts = _required_scripts_all_ok()
    scripts["bootstrap.sh"] = (
        "pwd > pwd_check.txt\n"
        "test -f README.md\n"
        "exit 0\n"
    )
    _add_scripts(proj, scripts)

    run_sandbox._do_sandbox("myproject", proj, "myproject-CWD")
    state = _read_latest_state(tmp_path)
    assert state["state"] == "validated"

    pwd_check = _sandbox_dir(tmp_path, "myproject-CWD") / "worktree" / "pwd_check.txt"
    assert pwd_check.exists(), "bootstrap must have run with worktree as cwd"
    recorded_pwd = pwd_check.read_text().strip()
    assert recorded_pwd.endswith("/worktree"), (
        f"expected cwd=<worktree>, got {recorded_pwd!r}"
    )


# ── Sandbox env injection (rule C1 + AI_DEV_FACTORY_RUNTIME_ROOT) ─────────────


def test_sandbox_runner_injects_required_env_vars(tmp_path, monkeypatch):
    """Every operational script must see the sandbox-allocated env vars
    in its environment. Without these the scripts fall back to the main
    runtime defaults (8080/3000/8090) and a sandbox healthcheck silently
    validates the MAIN runtime — the exact bug this PR fixes."""
    # Redirect the env dump files into tmp_path so the test is hermetic.
    dump_dir = tmp_path / "env_dump"
    dump_dir.mkdir()
    proj = _make_git_project(tmp_path)
    scripts = {
        name: (
            f'printenv API_PORT                       > "{dump_dir}/API_PORT" 2>/dev/null || true\n'
            f'printenv WEB_PORT                       > "{dump_dir}/WEB_PORT" 2>/dev/null || true\n'
            f'printenv AI_DEV_FACTORY_SUPERVISOR_PORT > "{dump_dir}/SUP_PORT" 2>/dev/null || true\n'
            f'printenv AI_DEV_FACTORY_SUPERVISOR_URL  > "{dump_dir}/SUP_URL"  2>/dev/null || true\n'
            f'printenv AI_DEV_FACTORY_RUNTIME_ROOT    > "{dump_dir}/RT_ROOT"  2>/dev/null || true\n'
            f'printenv COMPOSE_PROJECT_NAME           > "{dump_dir}/COMP"     2>/dev/null || true\n'
            f'printenv SANDBOX_ID                     > "{dump_dir}/SBID"     2>/dev/null || true\n'
            'exit 0\n'
        )
        for name in run_sandbox._REQUIRED_SCRIPTS
    }
    _add_scripts(proj, scripts)

    run_sandbox._do_sandbox("myproject", proj, "myproject-ENV")
    state = _read_latest_state(tmp_path)
    assert state["state"] == "validated", state

    # Every env file must exist and have a non-empty body. Empty body
    # means `printenv` didn't find the var (env not propagated).
    for key in ("API_PORT", "WEB_PORT", "SUP_PORT", "SUP_URL", "RT_ROOT", "COMP", "SBID"):
        path = dump_dir / key
        assert path.exists(), f"missing dump for {key}"
        assert path.read_text().strip(), f"env var {key} was empty in script env"

    # Spot-check actual values come from the sandbox allocation, not
    # the main-runtime defaults.
    api_port = (dump_dir / "API_PORT").read_text().strip()
    web_port = (dump_dir / "WEB_PORT").read_text().strip()
    sup_port = (dump_dir / "SUP_PORT").read_text().strip()
    sup_url  = (dump_dir / "SUP_URL").read_text().strip()
    rt_root  = (dump_dir / "RT_ROOT").read_text().strip()
    sbid     = (dump_dir / "SBID").read_text().strip()

    assert api_port.isdigit() and api_port != "8080", (
        f"API_PORT {api_port!r} should come from sandbox slot, never the "
        f"main-runtime default 8080"
    )
    assert web_port.isdigit() and web_port != "3000", (
        f"WEB_PORT {web_port!r} should come from sandbox slot, never the "
        f"main-runtime default 3000"
    )
    assert sup_port.isdigit() and sup_port != "8090", (
        f"AI_DEV_FACTORY_SUPERVISOR_PORT {sup_port!r} should come from "
        f"sandbox slot, never the main-runtime default 8090"
    )
    assert sup_url.startswith("http://host.docker.internal:"), sup_url
    assert sup_url.endswith(f":{sup_port}"), (
        f"SUPERVISOR_URL {sup_url!r} must point at SUPERVISOR_PORT {sup_port}"
    )
    assert sbid == "myproject-ENV", sbid

    # AI_DEV_FACTORY_RUNTIME_ROOT must point at the PER-SANDBOX runtime
    # tree, not the host-shared one. Otherwise scripts that resolve
    # state/logs paths would land in the main runtime tree.
    expected_runtime = _sandbox_dir(tmp_path, "myproject-ENV") / "runtime"
    assert Path(rt_root) == expected_runtime, (
        f"AI_DEV_FACTORY_RUNTIME_ROOT should be the per-sandbox runtime "
        f"(<sandbox>/runtime), got {rt_root!r}, expected {expected_runtime}"
    )


def test_sandbox_runner_supervisor_url_uses_allocated_port(tmp_path, monkeypatch):
    """The SUPERVISOR_URL injected into scripts must reflect the
    allocated SUPERVISOR_PORT — never the documented 8090 default."""
    dump_dir = tmp_path / "env_dump"
    dump_dir.mkdir()
    proj = _make_git_project(tmp_path)
    scripts = {
        name: (
            f'printenv AI_DEV_FACTORY_SUPERVISOR_PORT > "{dump_dir}/SUP_PORT_{name}"\n'
            f'printenv AI_DEV_FACTORY_SUPERVISOR_URL  > "{dump_dir}/SUP_URL_{name}"\n'
            "exit 0\n"
        )
        for name in run_sandbox._REQUIRED_SCRIPTS
    }
    _add_scripts(proj, scripts)
    run_sandbox._do_sandbox("myproject", proj, "myproject-URL")

    sup_port = (dump_dir / "SUP_PORT_bootstrap.sh").read_text().strip()
    sup_url  = (dump_dir / "SUP_URL_bootstrap.sh").read_text().strip()
    assert sup_url == f"http://host.docker.internal:{sup_port}", (
        f"supervisor URL must use allocated port, got url={sup_url!r} port={sup_port!r}"
    )
    # Cross-script consistency: every script sees the same URL.
    for name in run_sandbox._REQUIRED_SCRIPTS:
        per_script = (dump_dir / f"SUP_URL_{name}").read_text().strip()
        assert per_script == sup_url, (
            f"scripts disagree on SUPERVISOR_URL: {name}={per_script!r} vs {sup_url!r}"
        )


# ── Worktree robustness (preserved from PR #120) ──────────────────────────────


def test_worktree_log_header_contains_explicit_diagnostics(tmp_path):
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-HDR")

    log = _read_latest_log(tmp_path)
    assert "--- creating git worktree ---" in log
    assert "worktree path: " in log
    assert "timeout: " in log
    assert "git worktree add " in log
    assert "exit=0" in log


def test_worktree_subprocess_timeout_marks_failed(tmp_path, monkeypatch):
    """If ``git worktree add`` hangs, the worker must kill it and mark
    the sandbox as failed — never leave state=running forever."""
    proj = _make_git_project(tmp_path)

    real_popen = run_sandbox.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _Hanging:
                pid = 999999
                returncode = None

                def communicate(self, timeout=None):
                    raise run_sandbox.subprocess.TimeoutExpired(
                        cmd=cmd, timeout=timeout,
                    )
            return _Hanging()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(run_sandbox.os, "killpg", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_WORKTREE_TIMEOUT_SECONDS", 1)

    run_sandbox._do_sandbox("myproject", proj, "myproject-TO")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "timed out" in state["error"]
    assert state["last_step"] == "worktree"

    log = _read_latest_log(tmp_path)
    assert "git command timed out" in log
    assert "worktree creation failed" in log


def test_worktree_nonzero_exit_preserves_stderr(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)
    real_popen = run_sandbox.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _Failing:
                pid = 999998
                returncode = 128

                def communicate(self, timeout=None):
                    return ("", "fatal: HEAD is not a valid object name\n")
            return _Failing()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    run_sandbox._do_sandbox("myproject", proj, "myproject-ERR")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "exited 128" in state["error"]
    assert "fatal: HEAD" in state["error"]

    log = _read_latest_log(tmp_path)
    assert "fatal: HEAD" in log
    assert "exit=128" in log


def test_preflight_git_binary_missing(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(run_sandbox.shutil, "which", lambda name: None)
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "git binary not found" in err


def test_preflight_project_root_missing(tmp_path):
    log = tmp_path / "preflight.log"
    ghost = tmp_path / "does-not-exist"

    err = run_sandbox._preflight_worktree(ghost, ghost / "wt", log)
    assert err is not None
    assert "does not exist" in err


def test_preflight_project_root_not_a_git_repo(tmp_path):
    proj = tmp_path / "not-a-repo"
    proj.mkdir()
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "not a git repository" in err


def test_preflight_removes_stale_index_lock(tmp_path):
    proj = _make_git_project(tmp_path)
    lock = proj / ".git" / "index.lock"
    lock.write_text("")
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt-new", log)
    assert err is None
    assert not lock.exists()
    assert "removed stale lock" in log.read_text()


def test_create_worktree_happy_path(tmp_path):
    proj = _make_git_project(tmp_path)
    log = tmp_path / "run.log"
    wt = tmp_path / "wt"

    ok, err = run_sandbox._create_worktree(proj, wt, log)
    assert ok is True, f"unexpected error: {err}"
    assert wt.exists()
    log_text = log.read_text()
    assert "worktree path: " in log_text
    assert "worktree created" in log_text
    assert "exit=0" in log_text


def test_unhandled_exception_inside_create_worktree_is_finalised(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)

    def boom(*a, **kw):
        raise RuntimeError("simulated catastrophic failure")

    monkeypatch.setattr(run_sandbox, "_create_worktree", boom)
    run_sandbox._do_sandbox("myproject", proj, "myproject-BOOM")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "unhandled exception" in state["error"]
    assert "simulated catastrophic failure" in state["error"]


def test_state_never_stuck_in_running_after_failure(tmp_path, monkeypatch):
    """Belt-and-suspenders: state.json must never be left as 'running'."""
    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(run_sandbox.shutil, "which", lambda name: None)

    run_sandbox._do_sandbox("myproject", proj, "myproject-NEVER-STUCK")

    state = _read_latest_state(tmp_path)
    assert state["state"] != "running"
    assert state["state"] == "failed"


def test_run_git_uses_safe_subprocess_flags(monkeypatch, tmp_path):
    """``stdin=DEVNULL`` + ``start_new_session=True`` are the two flags
    that make timeout-killing reliable. Regress against any future
    refactor that drops them."""
    seen_kwargs = {}

    def fake_popen(cmd, *a, **kw):
        seen_kwargs.update(kw)

        class _Done:
            pid = 1
            returncode = 0

            def communicate(self, timeout=None):
                return ("", "")

        return _Done()

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    log = tmp_path / "log.txt"
    rc, _out, _err = run_sandbox._run_git(
        ["--version"], cwd=tmp_path, log_path=log, timeout=5
    )
    assert rc == 0
    assert seen_kwargs.get("stdin") is run_sandbox.subprocess.DEVNULL
    assert seen_kwargs.get("start_new_session") is True
    log_text = log.read_text()
    assert "+ git --version" in log_text
    assert "timeout=5s" in log_text
    assert "exit=0" in log_text


# ── CLI entry point (smoke) ───────────────────────────────────────────────────


def test_worker_cli_smoke(tmp_path):
    """``python tools/agent_runner/run_sandbox.py`` must succeed on a
    real git project — this is exactly how the supervisor invokes it."""
    proj = _make_git_project(tmp_path)
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    env = {
        **__import__("os").environ,
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(runtime_root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    script = Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "run_sandbox.py"
    result = _subprocess.run(
        [sys.executable, str(script),
         "--project-root", str(proj),
         "--project-id", "myproject"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    # exit code may be 1 because the test project has no scripts to run —
    # the important invariant is that the state file is finalised.
    assert result.returncode in (0, 1), (
        f"unexpected rc {result.returncode}: stderr={result.stderr[:500]}"
    )
    state = json.loads(
        (runtime_root / "state" / "sandbox-myproject.json").read_text()
    )
    assert state["state"] in ("success", "failed", "validated")
    assert state["finished_at"] is not None


# ── Lifecycle mode tests ──────────────────────────────────────────────────────


def test_validation_mode_writes_validated_state(tmp_path, monkeypatch):
    """In validation mode, a successful run writes state=validated."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())

    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    rc = run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="validation")
    assert rc == 0

    state = _read_latest_state(tmp_path)
    assert state["state"] == "validated"
    assert state["mode"] == "validation"
    assert state["finished_at"] is not None


def test_validation_mode_releases_port_slot_on_success(tmp_path, monkeypatch):
    """After validation mode succeeds, the port slot must be freed."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())

    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="validation")

    registry_path, _ = run_sandbox._port_registry_paths()
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
    assert sandbox_id not in registry


def test_environment_mode_writes_environment_state(tmp_path, monkeypatch):
    """In environment mode, a successful run writes state=environment."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())

    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    rc = run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="environment")
    assert rc == 0

    state = _read_latest_state(tmp_path)
    assert state["state"] == "environment"
    assert state["mode"] == "environment"
    assert state["finished_at"] is not None


def test_environment_mode_keeps_port_slot_allocated(tmp_path, monkeypatch):
    """After environment mode succeeds, the port slot must remain allocated."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, _required_scripts_all_ok())

    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="environment")

    registry_path, _ = run_sandbox._port_registry_paths()
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
    assert sandbox_id in registry, "port slot must remain allocated for environment mode"


def test_environment_mode_failure_releases_port_slot(tmp_path, monkeypatch):
    """Even in environment mode, a failed run must release the port slot."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {name: "exit 0" for name in run_sandbox._REQUIRED_SCRIPTS[:-1]})
    _add_scripts(proj, {"healthcheck.sh": "exit 1"})

    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    rc = run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="environment")
    assert rc == 1

    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"

    registry_path, _ = run_sandbox._port_registry_paths()
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
    assert sandbox_id not in registry


def test_validation_initial_state_is_validating(tmp_path, monkeypatch):
    """The first state write must use 'validating', not 'running'."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("PROJECT_NAME", "testproject")

    proj = _make_git_project(tmp_path)

    states_seen = []

    original_write = run_sandbox._write_state

    def capture_write(state_path, latest_path, data):
        states_seen.append(data.get("state"))
        original_write(state_path, latest_path, data)

    monkeypatch.setattr(run_sandbox, "_write_state", capture_write)
    monkeypatch.setattr(run_sandbox, "_start_sandbox_supervisor", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_stop_sandbox_supervisor", lambda *a, **kw: None)

    sandbox_id = run_sandbox._make_sandbox_id("myproject")
    run_sandbox._do_sandbox("myproject", proj, sandbox_id, mode="validation")

    assert states_seen[0] == "validating", (
        f"first state must be 'validating', got {states_seen[0]!r}"
    )
