"""Tests for T026 + T033 — checkpoint publishing and pre-flight dirty tree guard."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
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


# ── launch_ticket auto flags ───────────────────────────────────────────────────

def test_launch_ticket_passes_auto_commit_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_commit=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-commit" in cmd


def test_launch_ticket_passes_auto_push_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_push=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-push" in cmd


def test_launch_ticket_passes_auto_include_code_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_include_code=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-include-code" in cmd


def test_launch_ticket_no_auto_flags_by_default(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    cmd = mock_sub.call_args[0][0]
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
    mock_commit = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_commit) as mock_sub:
        result = _ensure_clean_working_tree("T001", auto_push=False)
    assert result is True
    cmd = mock_sub.call_args[0][0]
    assert "--commit" in cmd
    assert "--include-code" in cmd


def test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint():
    mock_commit = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon._classify_dirty_files", return_value=([], ["services/control_api/routes/tickets.py"], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_commit) as mock_sub:
        result = _ensure_clean_working_tree("T001", auto_push=False)
    assert result is True
    cmd = mock_sub.call_args[0][0]
    assert "--commit" in cmd
    assert "--include-code" in cmd


def test_ensure_clean_working_tree_code_scope_files_do_not_block_when_no_unknown():
    mock_commit = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon._classify_dirty_files", return_value=([], ["apps/dashboard/src/App.jsx"], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_commit):
        result = _ensure_clean_working_tree("T001")
    assert result is True


def test_ensure_clean_working_tree_checkpoint_failure_aborts():
    mock_fail = MagicMock(stdout="", stderr="error", returncode=2)
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_fail):
        result = _ensure_clean_working_tree("T001")
    assert result is False


def test_ensure_clean_working_tree_nothing_to_commit_proceeds():
    # returncode=1 from commit_ticket means nothing to commit — still proceed
    mock_nothing = MagicMock(stdout="", stderr="", returncode=1)
    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_nothing):
        result = _ensure_clean_working_tree("T001")
    assert result is True


def test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds():
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", side_effect=fake_run):
        result = _ensure_clean_working_tree("T001", auto_push=True)

    assert result is True
    push_calls = [c for c in subprocess_calls if "--push" in c]
    assert len(push_calls) == 1


def test_ensure_clean_working_tree_no_push_when_auto_push_false():
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", side_effect=fake_run):
        result = _ensure_clean_working_tree("T001", auto_push=False)

    assert result is True
    push_calls = [c for c in subprocess_calls if "--push" in c]
    assert push_calls == []


# ── launch_ticket: pre-flight integration ─────────────────────────────────────

def test_launch_ticket_aborts_when_unknown_dirty_files(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon._classify_dirty_files", return_value=([], [], ["some-user-file.py"])), \
         patch("run_daemon.subprocess.run", side_effect=fake_run):
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)

    run_ticket_calls = [c for c in subprocess_calls if "--auto" in c]
    assert run_ticket_calls == []


def test_launch_ticket_proceeds_after_auto_checkpoint(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon._classify_dirty_files", return_value=(["runs/T001/plan.md"], [], [])), \
         patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)

    all_calls = [c[0][0] for c in mock_sub.call_args_list]
    run_ticket_auto_calls = [c for c in all_calls if "--auto" in c]
    assert len(run_ticket_auto_calls) == 1
