"""Tests for T026 + T033 — checkpoint publishing and pre-flight dirty tree guard."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    CheckpointError,
    _classify_dirty_files,
    _ensure_clean_working_tree,
    launch_ticket,
    run_once,
)


def _write_state(runs_dir: Path, ticket_id: str, state: str) -> Path:
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    return run_dir


def _launch_preflight_ok(*, branch: str = "ticket/T001"):
    return patch.multiple(
        "run_daemon",
        _sync_ticket_branch=MagicMock(return_value=True),
        _ensure_clean_working_tree=MagicMock(return_value=True),
        _get_current_branch=MagicMock(return_value=branch),
    )


# ── launch_ticket auto flags ───────────────────────────────────────────────────

def test_launch_ticket_passes_auto_commit_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0, pid=4242)
    mock_result.poll.return_value = None
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=mock_result) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_commit=True)
    cmd = mock_spawn.call_args[0][0]
    assert "--auto-commit" in cmd


def test_launch_ticket_passes_auto_push_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0, pid=4242)
    mock_result.poll.return_value = None
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=mock_result) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_push=True)
    cmd = mock_spawn.call_args[0][0]
    assert "--auto-push" in cmd


def test_launch_ticket_passes_auto_include_code_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0, pid=4242)
    mock_result.poll.return_value = None
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=mock_result) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_include_code=True)
    cmd = mock_spawn.call_args[0][0]
    assert "--auto-include-code" in cmd


def test_launch_ticket_no_auto_flags_by_default(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0, pid=4242)
    mock_result.poll.return_value = None
    with _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=mock_result) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    cmd = mock_spawn.call_args[0][0]
    assert "--auto-commit" not in cmd
    assert "--auto-push" not in cmd
    assert "--auto-include-code" not in cmd


def test_run_once_passes_auto_flags_to_launch_ticket(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs, auto_commit=True, auto_push=True, auto_include_code=True)
    mock_launch.assert_called_once_with(
        "T001", "test-cmd", False, runs,
        worktrees_dir=None, auto_commit=True, auto_push=True, auto_include_code=True,
        state_dir=runs,
    )


# ── _classify_dirty_files ─────────────────────────────────────────────────────

def _git_status_mock(output: str, returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=output, stderr="", returncode=returncode)


def test_classify_dirty_files_clean_tree():
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock("")):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert workflow == []
    assert code_scope == []
    assert unknown == []


def test_classify_dirty_files_runs_files_are_workflow_artifacts():
    status = " M runs/T001/plan.md\n?? runs/.issue-intake.json\n"
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock(status)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert "runs/T001/plan.md" in workflow
    assert "runs/.issue-intake.json" in workflow
    assert code_scope == []
    assert unknown == []


def test_classify_dirty_files_code_scope_files_are_not_unknown():
    status = " M services/control_api/routes/tickets.py\n M apps/dashboard/src/pages/TicketDetailPage.jsx\n"
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock(status)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert workflow == []
    assert "services/control_api/routes/tickets.py" in code_scope
    assert "apps/dashboard/src/pages/TicketDetailPage.jsx" in code_scope
    assert unknown == []


def test_classify_dirty_files_non_scope_files_are_unknown():
    status = " M some-random-file.py\n M README.md\n"
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock(status)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert workflow == []
    assert "README.md" in code_scope
    assert "some-random-file.py" in unknown


def test_classify_dirty_files_mixed():
    status = " M runs/T001/plan.md\n M tools/run_ticket.py\n M mystery.sh\n"
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock(status)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert "runs/T001/plan.md" in workflow
    assert "tools/run_ticket.py" in code_scope
    assert "mystery.sh" in unknown


def test_classify_dirty_files_handles_rename_arrow():
    status = "R  old.py -> runs/T001/new.py\n"
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock(status)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert "runs/T001/new.py" in workflow


def test_classify_dirty_files_returns_empty_on_git_failure():
    with patch("run_daemon.subprocess.run", return_value=_git_status_mock("", returncode=1)):
        workflow, code_scope, unknown = _classify_dirty_files("T001")
    assert workflow == []
    assert code_scope == []
    assert unknown == []


# ── _ensure_clean_working_tree ────────────────────────────────────────────────

def test_ensure_clean_working_tree_returns_true_when_clean():
    with patch("run_daemon._classify_dirty_files", return_value=([], [], [])):
        result = _ensure_clean_working_tree("T001")
    assert result is True


def test_ensure_clean_working_tree_unknown_files_aborts():
    with patch("run_daemon._classify_dirty_files", return_value=([], [], ["mystery.py"])):
        result = _ensure_clean_working_tree("T001")
    assert result is False


def test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint():
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.checkpoint_transition") as mock_ckpt:
        result = _ensure_clean_working_tree("T001", auto_push=False)
    assert result is True
    mock_ckpt.assert_called_once_with(
        "T001",
        "T001: pre-flight checkpoint — persist dirty runtime artifacts",
        push=False,
        include_code=True,
    )


def test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint():
    with patch(
        "run_daemon._classify_dirty_files",
        return_value=([], ["services/control_api/routes/tickets.py"], []),
    ), patch("run_daemon.checkpoint_transition") as mock_ckpt:
        result = _ensure_clean_working_tree("T001", auto_push=False)
    assert result is True
    mock_ckpt.assert_called_once_with(
        "T001",
        "T001: pre-flight checkpoint — persist dirty runtime artifacts",
        push=False,
        include_code=True,
    )


def test_ensure_clean_working_tree_code_scope_files_do_not_block_when_no_unknown():
    with patch("run_daemon._classify_dirty_files", return_value=([], ["apps/dashboard/src/App.jsx"], [])), \
         patch("run_daemon.checkpoint_transition"):
        result = _ensure_clean_working_tree("T001")
    assert result is True


def test_ensure_clean_working_tree_checkpoint_failure_aborts():
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.checkpoint_transition", side_effect=CheckpointError("error")):
        result = _ensure_clean_working_tree("T001")
    assert result is False


def test_ensure_clean_working_tree_nothing_to_commit_proceeds():
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.checkpoint_transition"):
        result = _ensure_clean_working_tree("T001")
    assert result is True


def test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds():
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.checkpoint_transition") as mock_ckpt:
        result = _ensure_clean_working_tree("T001", auto_push=True)

    assert result is True
    assert mock_ckpt.call_args.kwargs["push"] is True


def test_ensure_clean_working_tree_no_push_when_auto_push_false():
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.checkpoint_transition") as mock_ckpt:
        result = _ensure_clean_working_tree("T001", auto_push=False)

    assert result is True
    assert mock_ckpt.call_args.kwargs["push"] is False


# ── launch_ticket: pre-flight integration ─────────────────────────────────────

def test_launch_ticket_aborts_when_unknown_dirty_files(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon._classify_dirty_files", return_value=([], [], ["some-user-file.py"])), \
         patch("run_daemon.subprocess.run", side_effect=fake_run), \
         patch("run_daemon._spawn_worker_process") as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)

    mock_spawn.assert_not_called()


def test_launch_ticket_proceeds_after_auto_checkpoint(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0, pid=4242)
    mock_result.poll.return_value = None

    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         _launch_preflight_ok(), \
         patch("run_daemon._spawn_worker_process", return_value=mock_result) as mock_spawn:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)

    cmd = mock_spawn.call_args[0][0]
    assert "--auto" in cmd
