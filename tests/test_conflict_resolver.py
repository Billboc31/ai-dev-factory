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
    monkeypatch.setattr(_rcr, "_purge_oversized_runtime_artifacts", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_unstage_noise_paths", lambda _tid: None)
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
    monkeypatch.setattr(_rcr, "_purge_oversized_runtime_artifacts", lambda _tid: None)
    monkeypatch.setattr(_rcr, "_unstage_noise_paths", lambda _tid: None)
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


def test_split_conflicts_treats_foreign_runs_and_node_modules_as_runtime():
    import run_conflict_resolver as rcr

    files = [
        "frontend/src/App.tsx",
        "runs/T011/conflict/context.md",
        "runs/T014/prompts/conflict-resolver-attempt-1.md",
        "runs/T025/state.json",
        "frontend/node_modules/lru-cache/package.json",
        "node_modules/.package-lock.json",
        "backend/target/surefire-reports/TEST-Foo.xml",
        "frontend/dist/index.html",
    ]
    source, runtime = rcr._split_conflicts("T025", files)
    assert source == ["frontend/src/App.tsx"]
    assert runtime == [
        "runs/T011/conflict/context.md",
        "runs/T014/prompts/conflict-resolver-attempt-1.md",
        "runs/T025/state.json",
        "frontend/node_modules/lru-cache/package.json",
        "node_modules/.package-lock.json",
        "backend/target/surefire-reports/TEST-Foo.xml",
        "frontend/dist/index.html",
    ]


def test_auto_resolve_runtime_keeps_own_ticket_takes_upstream_for_foreign(
    monkeypatch,
):
    import run_conflict_resolver as rcr

    calls: list[list[str]] = []

    def _fake_git(args):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    rcr._auto_resolve_runtime_conflicts(
        "T025",
        [
            "runs/T025/state.json",
            "runs/T011/conflict/context.md",
            "frontend/node_modules/foo/package.json",
        ],
    )
    assert ["checkout", "--theirs", "--", "runs/T025/state.json"] in calls
    assert ["checkout", "--ours", "--", "runs/T011/conflict/context.md"] in calls
    assert ["checkout", "--ours", "--", "frontend/node_modules/foo/package.json"] in calls


def test_blocking_dirty_paths_ignores_foreign_runs_and_node_modules():
    import run_conflict_resolver as rcr

    porcelain = "\n".join([
        " M runs/T011/state.json",
        " M frontend/node_modules/lru-cache/package.json",
        " M frontend/src/App.tsx",
        " M runs/T025/runtime.log",
    ])
    assert rcr._blocking_dirty_paths(porcelain, "T025") == ["frontend/src/App.tsx"]


def test_scrub_ticket_runtime_dir_resets_whole_runtime_prefix(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    calls: list[list[str]] = []

    def _fake_git(args):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    rcr._scrub_ticket_runtime_dir("T010")
    assert ["checkout", "HEAD", "--", "runs/T010/"] in calls
    assert [
        "clean", "-fd", "-e", "retry-state.json", "--", "runs/T010",
    ] in calls


def test_quarantine_moves_untracked_blockers(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    junk = tmp_path / "apps" / "api" / "migrations" / "0002_dup.sql"
    junk.parent.mkdir(parents=True)
    junk.write_text("-- dup\n", encoding="utf-8")

    def _fake_git(args):
        if args[:2] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout="?? apps/api/migrations/0002_dup.sql\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    remaining = rcr._quarantine_untracked_blocking_paths(
        ticket_id, ["apps/api/migrations/0002_dup.sql", "README.md"],
    )
    assert remaining == ["README.md"]
    assert not junk.exists()
    quarantined = (
        tmp_path / "runs" / ticket_id / "conflict" / "quarantine"
        / "apps" / "api" / "migrations" / "0002_dup.sql"
    )
    assert quarantined.exists()


def test_prepare_clean_tree_quarantines_untracked_then_succeeds(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    (tmp_path / "runs" / ticket_id).mkdir(parents=True)
    junk = tmp_path / "apps" / "api" / "migrations" / "0002_dup.sql"
    junk.parent.mkdir(parents=True)
    junk.write_text("-- dup\n", encoding="utf-8")

    def _fake_git(args):
        if args[:3] == ["status", "--porcelain", "--"]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:2] == ["status", "--porcelain"]:
            if junk.exists():
                return subprocess.CompletedProcess(
                    args, 0,
                    stdout="?? apps/api/migrations/0002_dup.sql\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    monkeypatch.setattr(rcr, "_scrub_ticket_runtime_dir", lambda _tid: None)
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is True
    assert not junk.exists()


def test_prepare_clean_tree_for_rebase_fails_when_runtime_still_dirty(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)

    def _fake_git(args):
        if args[:3] == ["status", "--porcelain", "--"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=" M runs/T010/state.json\n", stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is False


def test_prepare_clean_tree_tolerates_retry_state_json(tmp_path, monkeypatch):
    import run_conflict_resolver as rcr

    ticket_id = "T010"
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)

    def _fake_git(args):
        if args[:3] == ["status", "--porcelain", "--"]:
            return subprocess.CompletedProcess(
                args, 0, stdout="?? runs/T010/retry-state.json\n", stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rcr, "_run_git", _fake_git)
    assert rcr._prepare_clean_tree_for_rebase(ticket_id) is True


def test_advance_past_runtime_retries_when_continue_hits_target_conflicts(
    tmp_path, monkeypatch,
):
    """rebase --continue that only conflicts on build artifacts must not abort."""
    import run_conflict_resolver as rcr

    run_dir = tmp_path / "runs" / "T025"
    run_dir.mkdir(parents=True)
    data: dict = {}
    calls = {"list": 0, "continue": 0, "auto": 0}
    pending_target = ["backend/target/surefire-reports/x.xml"]

    def _fake_list():
        calls["list"] += 1
        if calls["auto"] == 0 and calls["continue"] >= 1:
            return list(pending_target)
        return []

    def _fake_continue(_tid):
        calls["continue"] += 1
        if calls["continue"] == 1:
            return subprocess.CompletedProcess(
                ["git", "rebase", "--continue"],
                1,
                stdout="",
                stderr="CONFLICT (content): Merge conflict in backend/target/x\n",
            )
        return subprocess.CompletedProcess(
            ["git", "rebase", "--continue"], 0, stdout="", stderr="",
        )

    def _fake_auto(_tid, paths):
        calls["auto"] += 1
        assert paths == pending_target
        pending_target.clear()

    rebase_alive = {"v": True}

    def _fake_rebase_in_progress():
        return rebase_alive["v"]

    def _fake_continue_and_maybe_done(_tid):
        result = _fake_continue(_tid)
        if result.returncode == 0:
            rebase_alive["v"] = False
        return result

    monkeypatch.setattr(rcr, "_list_conflicted_files", _fake_list)
    monkeypatch.setattr(rcr, "_effective_source_conflicts", lambda _tid: [])
    monkeypatch.setattr(rcr, "_rebase_in_progress", _fake_rebase_in_progress)
    monkeypatch.setattr(rcr, "_run_rebase_continue", _fake_continue_and_maybe_done)
    monkeypatch.setattr(rcr, "_auto_resolve_runtime_conflicts", _fake_auto)
    monkeypatch.setattr(rcr, "_log", lambda *_a, **_k: None)
    monkeypatch.setattr(rcr, "_write_error_log", lambda *_a, **_k: None)
    monkeypatch.setattr(rcr, "_persist_conflict_state", lambda *_a, **_k: None)

    result = rcr._advance_past_runtime_conflicts("T025", run_dir, data)
    assert result == []
    assert calls["auto"] >= 1
    assert calls["continue"] >= 1


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


def test_has_conflict_markers_ignores_source_that_mentions_markers(tmp_path):
    """Resolver source/fixtures mention <<<<<<< but must not fail every pass."""
    import run_conflict_resolver as rcr

    mention = tmp_path / "mention.py"
    mention.write_text('return "<<<<<<< " in text\n')
    real = tmp_path / "real.txt"
    real.write_text("<<<<<<< ours\na\n=======\nb\n>>>>>>> theirs\n")

    assert rcr._has_conflict_markers(str(mention)) is False
    assert rcr._has_conflict_markers(str(real)) is True
    # Live source files that previously caused perpetual CONFLICT_RESOLUTION_FAILED
    assert rcr._has_conflict_markers("tools/agent_runner/run_conflict_resolver.py") is False
    assert rcr._has_conflict_markers("tests/test_conflict_resolver.py") is False

