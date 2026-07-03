"""Tests for T143 — conflict detection and CONFLICT_RESOLUTION_* states."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_ticket import VALID_STATES, TRANSITIONS
from run_daemon import (
    AUTO_RUNNABLE_STATES,
    HUMAN_GATE_STATES,
    _load_state_json,
    _save_state_json,
    detect_pr_conflict,
)


# ── VALID_STATES ──────────────────────────────────────────────────────────────

def test_conflict_resolution_needed_in_valid_states():
    assert "CONFLICT_RESOLUTION_NEEDED" in VALID_STATES


def test_conflict_resolution_failed_in_valid_states():
    assert "CONFLICT_RESOLUTION_FAILED" in VALID_STATES


def test_conflict_resolving_in_valid_states():
    assert "CONFLICT_RESOLVING" in VALID_STATES


def test_conflict_resolved_review_needed_in_valid_states():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" in VALID_STATES


# ── AUTO_RUNNABLE_STATES ──────────────────────────────────────────────────────

def test_conflict_resolution_needed_not_auto_runnable():
    assert "CONFLICT_RESOLUTION_NEEDED" not in AUTO_RUNNABLE_STATES


def test_conflict_resolution_failed_not_auto_runnable():
    assert "CONFLICT_RESOLUTION_FAILED" not in AUTO_RUNNABLE_STATES


def test_conflict_resolving_not_auto_runnable():
    assert "CONFLICT_RESOLVING" not in AUTO_RUNNABLE_STATES


def test_conflict_resolved_review_needed_not_auto_runnable():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" not in AUTO_RUNNABLE_STATES


# ── HUMAN_GATE_STATES ─────────────────────────────────────────────────────────

def test_conflict_resolution_needed_in_human_gate():
    assert "CONFLICT_RESOLUTION_NEEDED" in HUMAN_GATE_STATES


def test_conflict_resolution_failed_in_human_gate():
    assert "CONFLICT_RESOLUTION_FAILED" in HUMAN_GATE_STATES


def test_conflict_resolved_review_needed_in_human_gate():
    assert "CONFLICT_RESOLVED_REVIEW_NEEDED" in HUMAN_GATE_STATES


# ── TRANSITIONS ───────────────────────────────────────────────────────────────

def test_conflict_resolution_failed_is_terminal():
    assert "CONFLICT_RESOLUTION_FAILED" not in TRANSITIONS


def test_conflict_resolution_needed_is_not_in_transitions():
    assert "CONFLICT_RESOLUTION_NEEDED" not in TRANSITIONS


# ── detect_pr_conflict — gh returns CONFLICTING ───────────────────────────────

def _make_run_dir(tmp_path: Path, ticket_id: str = "T001", **extra) -> Path:
    run_dir = tmp_path / ticket_id
    run_dir.mkdir(parents=True)
    state = {"ticket_id": ticket_id, "state": "IMPLEMENTATION_REVIEW_NEEDED", "pr_number": 42, **extra}
    (run_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return run_dir


def _mock_gh_conflicting(files=None):
    files = files or [{"path": "src/foo.py"}, {"path": "src/bar.py"}]
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "CONFLICTING"}))
    files_response = MagicMock(returncode=0, stdout=json.dumps({"files": files}))
    return [mergeable_response, files_response]


def test_detect_pr_conflict_returns_true_on_conflicting(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting()):
        result = detect_pr_conflict("T001", 42, run_dir, repo=None)
    assert result is True


def test_detect_pr_conflict_writes_metadata_to_state_json(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting()):
        detect_pr_conflict("T001", 42, run_dir, repo=None)
    data = _load_state_json(run_dir)
    assert data["state"] == "CONFLICT_RESOLUTION_NEEDED"
    assert data["pre_conflict_state"] == "IMPLEMENTATION_REVIEW_NEEDED"
    assert data["conflict_pr_number"] == 42
    assert "conflict_detected_at" in data
    assert isinstance(data["conflicted_files"], list)


def test_detect_pr_conflict_captures_file_list(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    files = [{"path": "tools/foo.py"}, {"path": "services/bar.py"}]
    with patch("run_daemon.subprocess.run", side_effect=_mock_gh_conflicting(files)):
        detect_pr_conflict("T001", 42, run_dir)
    data = _load_state_json(run_dir)
    assert "tools/foo.py" in data["conflicted_files"]
    assert "services/bar.py" in data["conflicted_files"]


# ── detect_pr_conflict — gh returns non-conflicting ──────────────────────────

def test_detect_pr_conflict_returns_false_when_mergeable(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "MERGEABLE"}))
    with patch("run_daemon.subprocess.run", return_value=mergeable_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_does_not_modify_state_when_not_conflicting(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    original = _load_state_json(run_dir)
    mergeable_response = MagicMock(returncode=0, stdout=json.dumps({"mergeable": "MERGEABLE"}))
    with patch("run_daemon.subprocess.run", return_value=mergeable_response):
        detect_pr_conflict("T001", 42, run_dir)
    data = _load_state_json(run_dir)
    assert data["state"] == original["state"]


# ── detect_pr_conflict — gh failure ──────────────────────────────────────────

def test_detect_pr_conflict_returns_false_on_gh_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    error_response = MagicMock(returncode=1, stdout="", stderr="Not found")
    with patch("run_daemon.subprocess.run", return_value=error_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_returns_false_when_gh_missing(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.subprocess.run", side_effect=FileNotFoundError):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


def test_detect_pr_conflict_returns_false_on_invalid_json(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    bad_response = MagicMock(returncode=0, stdout="not-json")
    with patch("run_daemon.subprocess.run", return_value=bad_response):
        result = detect_pr_conflict("T001", 42, run_dir)
    assert result is False


# ── TicketSummary — conflict fields serialised ────────────────────────────────

def test_ticket_summary_serialises_conflict_fields():
    from services.control_api.models.schemas import TicketSummary

    ts = TicketSummary(
        ticket_id="T001",
        state="CONFLICT_RESOLUTION_NEEDED",
        conflict_status="CONFLICT_RESOLUTION_NEEDED",
        conflicted_files=["src/foo.py"],
        conflict_detected_at="2026-05-23T12:00:00Z",
        pre_conflict_state="PLAN_APPROVED",
    )
    d = ts.model_dump()
    assert d["conflict_status"] == "CONFLICT_RESOLUTION_NEEDED"
    assert d["conflicted_files"] == ["src/foo.py"]
    assert d["conflict_detected_at"] == "2026-05-23T12:00:00Z"
    assert d["pre_conflict_state"] == "PLAN_APPROVED"


def test_ticket_summary_conflict_fields_default_to_none():
    from services.control_api.models.schemas import TicketSummary

    ts = TicketSummary(ticket_id="T001", state="PLAN_APPROVED")
    assert ts.conflict_status is None
    assert ts.conflicted_files is None
    assert ts.conflict_detected_at is None
    assert ts.pre_conflict_state is None
    assert ts.conflict_error is None


def test_get_ticket_exposes_conflict_error_from_error_log(isolated_tmp):
    from fastapi.testclient import TestClient

    run_dir = _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_FAILED")
    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True)
    (conflict_dir / "error.log").write_text(
        "[2026-07-03T14:32:34Z] failed to prepare clean tree before rebase\n",
        encoding="utf-8",
    )
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] == "CONFLICT_RESOLUTION_FAILED"
    assert "failed to prepare clean tree" in body["conflict_error"]


# ── GET /tickets/{id} returns conflict fields ─────────────────────────────────

def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    return create_app(project_root=tmp_path)


def _make_ticket(tmp_path: Path, ticket_id: str, state: str, **extra) -> Path:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    data = {"ticket_id": ticket_id, "state": state, **extra}
    (run_dir / "state.json").write_text(json.dumps(data), encoding="utf-8")
    return run_dir


@pytest.fixture()
def isolated_tmp(tmp_path, monkeypatch):
    """tmp_path with AI_DEV_FACTORY_RUNTIME_ROOT cleared so resolve_runs_dir uses tmp_path."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    return tmp_path


def test_get_ticket_exposes_conflict_fields(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(
        isolated_tmp, "T001", "CONFLICT_RESOLUTION_NEEDED",
        pre_conflict_state="PLAN_APPROVED",
        conflict_detected_at="2026-05-23T10:00:00Z",
        conflict_pr_number=7,
        conflicted_files=["a.py", "b.py"],
    )
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] == "CONFLICT_RESOLUTION_NEEDED"
    assert body["pre_conflict_state"] == "PLAN_APPROVED"
    assert body["conflict_detected_at"] == "2026-05-23T10:00:00Z"
    assert body["conflicted_files"] == ["a.py", "b.py"]


def test_get_ticket_conflict_fields_null_when_no_conflict(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.get("/tickets/T001")
    assert r.status_code == 200
    body = r.json()
    assert body["conflict_status"] is None
    assert body["conflicted_files"] is None


# ── POST /mark-conflict-failed ────────────────────────────────────────────────

def test_mark_conflict_failed_transitions_state(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_NEEDED",
                 pre_conflict_state="PLAN_APPROVED",
                 conflict_detected_at="2026-05-23T10:00:00Z",
                 conflicted_files=[])
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    state_file = isolated_tmp / "runs" / "T001" / "state.json"
    data = json.loads(state_file.read_text())
    assert data["state"] == "CONFLICT_RESOLUTION_FAILED"


def test_mark_conflict_failed_returns_409_from_wrong_state(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "PLAN_APPROVED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 409


def test_mark_conflict_failed_returns_409_from_conflict_resolution_failed(isolated_tmp):
    from fastapi.testclient import TestClient

    _make_ticket(isolated_tmp, "T001", "CONFLICT_RESOLUTION_FAILED")
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T001/mark-conflict-failed")
    assert r.status_code == 409


def test_mark_conflict_failed_returns_404_on_unknown_ticket(isolated_tmp):
    from fastapi.testclient import TestClient

    (isolated_tmp / "runs").mkdir(parents=True)
    client = TestClient(_make_app(isolated_tmp))
    r = client.post("/tickets/T999/mark-conflict-failed")
    assert r.status_code == 404


# ── CONFLICT_RESOLUTION_FAILED is terminal ────────────────────────────────────

def test_conflict_resolution_failed_has_no_outgoing_transitions():
    assert TRANSITIONS.get("CONFLICT_RESOLUTION_FAILED", "NOT_PRESENT") == "NOT_PRESENT"


# ── resolve_conflicts — multi-pass and max-pass tests ─────────────────────────

import run_conflict_resolver as _rcr  # noqa: E402  (after sys.path setup above)


def _make_resolver_fixture(tmp_path: Path, ticket_id: str = "T001") -> tuple[Path, Path]:
    """Return (run_dir, context_path) after creating the minimum fixture."""
    branch = "ticket/test-branch"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    state = {"ticket_id": ticket_id, "state": "CONFLICT_RESOLVING", "branch": branch}
    (run_dir / "state.json").write_text(json.dumps(state, indent=2))

    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir()
    context_path = conflict_dir / "context.md"
    context_path.write_text("# context\n")

    prompt_dir = tmp_path / "prompts" / "generic"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "conflict-resolver.md").write_text("# Resolve\n")

    return run_dir, context_path


def _git_ok(stdout: str = "") -> MagicMock:
    return MagicMock(returncode=0, stdout=stdout, stderr="")


def _git_fail(stderr: str = "error", stdout: str = "") -> MagicMock:
    return MagicMock(returncode=1, stdout=stdout, stderr=stderr)


def test_resolve_conflicts_multi_pass_success(tmp_path, monkeypatch):
    """Two-pass scenario: pass 1 leaves one file conflicted, pass 2 clears all.

    Expected: state → CONFLICT_RESOLVED_REVIEW_NEEDED, return 0.
    """
    ticket_id = "T001"
    run_dir, context_path = _make_resolver_fixture(tmp_path, ticket_id)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(_rcr, "collect_context", MagicMock(return_value=context_path))
    monkeypatch.setattr(_rcr, "execute_external_command", MagicMock(return_value=("ok", "", 0)))
    monkeypatch.setattr(_rcr, "compose_runtime_prompt", MagicMock(return_value="prompt"))
    monkeypatch.setattr(_rcr, "_run_tests", MagicMock(return_value="Exit code: 0\n"))
    monkeypatch.setattr(_rcr, "_prepare_clean_tree_for_rebase", lambda _tid: True)
    monkeypatch.setattr(_rcr, "_scrub_runtime_noise_before_rebase", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_rebase_in_progress", lambda: False)
    advance_seq = iter([
        ["file_a.py", "file_b.py"],
        ["file_b.py"],
        [],
    ])
    monkeypatch.setattr(
        _rcr,
        "_advance_past_runtime_conflicts",
        lambda *args, **kwargs: next(advance_seq, []),
    )
    monkeypatch.setattr(
        _rcr,
        "_run_rebase_continue",
        lambda _tid: MagicMock(returncode=0, stdout="", stderr=""),
    )

    subprocess_calls = [
        # _get_current_branch
        _git_ok("ticket/test-branch\n"),
        # git fetch origin
        _git_ok(),
        # git rebase origin/main → conflict
        _git_fail("CONFLICT"),
        # _list_conflicted_files (initial)
        _git_ok("file_a.py\nfile_b.py\n"),
        # Pass 1: git add -- file_a.py file_b.py
        _git_ok(),
        # Pass 2: git add -- file_b.py
        _git_ok(),
        # git add -A (artifacts)
        _git_ok(),
        # git commit
        _git_ok("[branch abc1234]"),
        # git rev-parse --short HEAD
        _git_ok("abc1234"),
        # git push --force-with-lease
        _git_ok(),
    ]

    with patch("run_conflict_resolver.subprocess.run", side_effect=subprocess_calls):
        rc = _rcr.resolve_conflicts(ticket_id, exec_cmd="dummy")

    assert rc == 0
    state = json.loads((run_dir / "state.json").read_text())
    assert state["state"] == "CONFLICT_RESOLVED_REVIEW_NEEDED"


def test_resolve_conflicts_max_pass_failure(tmp_path, monkeypatch):
    """All passes leave conflicts unresolved.

    Expected: git rebase --abort called, state → CONFLICT_RESOLUTION_FAILED, return 2.
    """
    ticket_id = "T001"
    run_dir, context_path = _make_resolver_fixture(tmp_path, ticket_id)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(_rcr, "collect_context", MagicMock(return_value=context_path))
    monkeypatch.setattr(_rcr, "execute_external_command", MagicMock(return_value=("ok", "", 0)))
    monkeypatch.setattr(_rcr, "compose_runtime_prompt", MagicMock(return_value="prompt"))
    monkeypatch.setattr(_rcr, "_prepare_clean_tree_for_rebase", lambda _tid: True)
    monkeypatch.setattr(_rcr, "_scrub_runtime_noise_before_rebase", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_rebase_in_progress", lambda: False)
    monkeypatch.setattr(
        _rcr,
        "_advance_past_runtime_conflicts",
        lambda *args, **kwargs: ["file_a.py"],
    )
    monkeypatch.setattr(
        _rcr,
        "_run_rebase_continue",
        lambda _tid: MagicMock(returncode=1, stdout="", stderr="CONFLICT"),
    )

    max_passes = _rcr.MAX_RESOLVER_PASSES

    subprocess_calls = [
        # _get_current_branch
        _git_ok("ticket/test-branch\n"),
        # git fetch origin
        _git_ok(),
        # git rebase origin/main → conflict
        _git_fail("CONFLICT"),
        # _list_conflicted_files (initial)
        _git_ok("file_a.py\n"),
    ]
    for _ in range(max_passes):
        subprocess_calls += [
            # git add -- file_a.py
            _git_ok(),
            # git rebase --continue → conflict persists
            _git_fail("CONFLICT"),
            # _list_conflicted_files → still conflicted
            _git_ok("file_a.py\n"),
        ]
    # git rebase --abort
    subprocess_calls.append(_git_ok())

    abort_calls: list[list[str]] = []

    original_run = _rcr._run_git

    def _tracking_run_git(args: list[str]) -> MagicMock:
        if args == ["rebase", "--abort"]:
            abort_calls.append(args)
        return original_run(args)

    with patch("run_conflict_resolver.subprocess.run", side_effect=subprocess_calls):
        monkeypatch.setattr(_rcr, "_run_git", _tracking_run_git)
        rc = _rcr.resolve_conflicts(ticket_id, exec_cmd="dummy")

    assert rc == 2
    state = json.loads((run_dir / "state.json").read_text())
    assert state["state"] == "CONFLICT_RESOLUTION_FAILED"
    assert len(abort_calls) >= 1, "git rebase --abort must be called on max-pass failure"


def test_blocking_dirty_paths_ignores_runtime_noise():
    import run_conflict_resolver as rcr

    porcelain = "\n".join([
        " M runs/T010/runtime.log",
        " M runs/T010/daemon.lock",
        "?? runs/T010/conflict/error.log",
        "?? runs/T010/prompts/conflict-resolver-attempt-1.md",
        " M README.md",
    ])
    assert rcr._blocking_dirty_paths(porcelain, "T010") == ["README.md"]


def test_split_conflicts_separates_runtime_paths():
    import run_conflict_resolver as rcr

    files = [
        "README.md",
        "runs/T010/state.json",
        "runs/T010/plan.md",
        "docs/architecture.md",
    ]
    source, runtime = rcr._split_conflicts("T010", files)
    assert source == ["README.md", "docs/architecture.md"]
    assert runtime == ["runs/T010/state.json", "runs/T010/plan.md"]


def test_prepare_clean_tree_for_rebase_ignores_runtime_log(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    state_file = run_dir / "state.json"
    state_file.write_text(
        json.dumps({"ticket_id": ticket_id, "state": "CONFLICT_RESOLUTION_NEEDED"}),
        encoding="utf-8",
    )
    (run_dir / "runtime.log").write_text("log\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", lambda args: subprocess.CompletedProcess(args, 0, stdout="", stderr=""))
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is True


def test_conflict_resolution_eligible_from_git_conflicts(tmp_path):
    import subprocess as sp
    from conflict_resolution_eligibility import conflict_resolution_eligible, git_conflicted_files

    wt = tmp_path / "wt"
    wt.mkdir()
    sp.run(["git", "init"], cwd=wt, capture_output=True, check=True)
    sp.run(["git", "config", "user.email", "t@test"], cwd=wt, capture_output=True)
    sp.run(["git", "config", "user.name", "t"], cwd=wt, capture_output=True)
    (wt / "f.txt").write_text("<<<<<<< ours\na\n=======\nb\n>>>>>>> theirs\n")
    sp.run(["git", "add", "f.txt"], cwd=wt, capture_output=True)
    sp.run(["git", "commit", "-m", "c"], cwd=wt, capture_output=True)

    state = {"state": "IMPLEMENTATION_REVIEW_NEEDED"}
    assert conflict_resolution_eligible(state, wt) is False
    assert git_conflicted_files(wt) == []

