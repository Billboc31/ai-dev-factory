"""Tests for the intake preflight that auto-ignores runtime/generated dirty files.

Hotfix scope:
  - Real source-tree changes still block intake (refused).
  - Generated/runtime files (__pycache__/*.pyc, runs/.project-map*.json,
    runs/daemon.log, runs/<ticket>/runtime.log, etc.) must not block intake;
    they are auto-restored and intake proceeds.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from runtime_checkpoint import (
    classify_intake_dirty_paths,
    is_ignorable_runtime_dirty_path,
    parse_porcelain_paths,
)
from run_issue_intake import IntakeError, check_working_tree_clean


def _cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ── is_ignorable_runtime_dirty_path ───────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc",
        "tests/__pycache__/test_daemon.cpython-314.pyc",
        "services/control_api/routes/__pycache__/health.cpython-314.pyc",
        "some/deep/path/__pycache__/foo.pyc",
        "runs/.project-map.json",
        "runs/.project-map-activity.json",
        "runs/.issue-intake.json",
        "runs/workers.json",
        "runs/daemon.log",
        "runs/daemon.pid",
        "runs/runtime.log",
        "runs/T111/runtime.log",
        "runs/T999/runtime.log",
        ".runtime/ai-dev-factory.sqlite",
        ".runtime/ai-dev-factory.sqlite-wal",
        ".runtime/ai-dev-factory.sqlite-shm",
        "some/other.sqlite",
        # Build / deps noise — must never be auto-committed (LLM + conflict tax)
        "frontend/node_modules/lodash/package.json",
        "apps/dashboard/node_modules/react/index.js",
        "node_modules/.package-lock.json",
        "backend/target/classes/Foo.class",
        "frontend/dist/assets/index.js",
        "apps/dashboard/dist/index.html",
        "frontend/node_modules/.vite/vitest/results.json",
    ],
)
def test_is_ignorable_runtime_dirty_path_recognises_runtime_files(path: str) -> None:
    assert is_ignorable_runtime_dirty_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "tools/agent_runner/run_daemon.py",
        "tools/agent_runner/run_issue_intake.py",
        "services/control_api/services/board_service.py",
        "tests/test_daemon_issue_polling.py",
        "README.md",
        "runs/T111/state.json",
        "runs/T111/ticket.md",
        "runs/T111/plan.md",
        ".gitignore",
        "",
    ],
)
def test_is_ignorable_runtime_dirty_path_keeps_real_files(path: str) -> None:
    assert is_ignorable_runtime_dirty_path(path) is False


# ── classify_intake_dirty_paths ───────────────────────────────────────────────


def test_classify_intake_dirty_paths_splits_correctly() -> None:
    paths = [
        "runs/.project-map.json",
        "tools/agent_runner/__pycache__/run_daemon.cpython-314.pyc",
        "tools/agent_runner/run_daemon.py",
        "runs/T111/runtime.log",
        "tests/test_daemon_issue_polling.py",
    ]
    ignorable, real = classify_intake_dirty_paths(paths)
    assert ignorable == [
        "runs/.project-map.json",
        "tools/agent_runner/__pycache__/run_daemon.cpython-314.pyc",
        "runs/T111/runtime.log",
    ]
    assert real == [
        "tools/agent_runner/run_daemon.py",
        "tests/test_daemon_issue_polling.py",
    ]


def test_classify_intake_dirty_paths_all_ignorable() -> None:
    paths = [
        "runs/.project-map.json",
        "tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc",
    ]
    ignorable, real = classify_intake_dirty_paths(paths)
    assert real == []
    assert set(ignorable) == set(paths)


def test_classify_intake_dirty_paths_empty() -> None:
    ignorable, real = classify_intake_dirty_paths([])
    assert ignorable == []
    assert real == []


# ── parse_porcelain_paths ─────────────────────────────────────────────────────


def test_parse_porcelain_paths_basic() -> None:
    raw = (
        " M runs/.project-map.json\n"
        "M  tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc\n"
        "?? runs/workers.json\n"
    )
    assert parse_porcelain_paths(raw) == [
        "runs/.project-map.json",
        "tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc",
        "runs/workers.json",
    ]


def test_parse_porcelain_paths_handles_rename() -> None:
    raw = "R  old/path.py -> new/path.py\n"
    assert parse_porcelain_paths(raw) == ["new/path.py"]


# ── check_working_tree_clean: runtime-only is OK ──────────────────────────────


def test_check_working_tree_clean_passes_when_only_runtime_dirty(capsys) -> None:
    """The exact scenario from the hotfix ticket: only runtime/generated files dirty."""
    porcelain = (
        " M runs/.project-map.json\n"
        "M  tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc\n"
    )

    calls: list[list[str]] = []
    state = {"first": True}

    def fake_run(args):
        calls.append(args)
        if args[:2] == ["git", "status"]:
            if state["first"]:
                state["first"] = False
                return _cp(stdout=porcelain)
            # After cleanup, tree is clean
            return _cp(stdout="")
        if args[:3] == ["git", "checkout", "HEAD"]:
            return _cp()
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        check_working_tree_clean()

    out = capsys.readouterr().out
    assert "intake preflight: ignored runtime dirty files" in out
    assert "intake preflight: clean enough to continue" in out

    checkout_paths = [a[-1] for a in calls if a[:3] == ["git", "checkout", "HEAD"]]
    assert "runs/.project-map.json" in checkout_paths
    assert "tools/agent_runner/__pycache__/runtime_db.cpython-314.pyc" in checkout_paths


# ── check_working_tree_clean: real code change still blocks ───────────────────


def test_check_working_tree_clean_refuses_real_code_change() -> None:
    porcelain = " M tools/agent_runner/run_daemon.py\n"

    def fake_run(args):
        if args[:2] == ["git", "status"]:
            return _cp(stdout=porcelain)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        with pytest.raises(IntakeError, match="working tree"):
            check_working_tree_clean()


def test_check_working_tree_clean_refuses_mixed_real_and_runtime() -> None:
    """Even with runtime noise present, any real dirty file must block intake."""
    porcelain = (
        " M runs/.project-map.json\n"
        " M tools/agent_runner/run_daemon.py\n"
    )

    def fake_run(args):
        if args[:2] == ["git", "status"]:
            return _cp(stdout=porcelain)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        with pytest.raises(IntakeError, match="working tree"):
            check_working_tree_clean()


# ── check_working_tree_clean: already clean (regression) ──────────────────────


def test_check_working_tree_clean_passes_when_already_clean() -> None:
    def fake_run(args):
        if args[:2] == ["git", "status"]:
            return _cp(stdout="")
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        check_working_tree_clean()  # must not raise


# ── check_working_tree_clean: SQLite DBs are tolerated but never restored ─────


def test_check_working_tree_clean_does_not_restore_sqlite_db(capsys) -> None:
    """Live SQLite runtime DBs must be classified as ignorable but never
    overwritten by `git checkout HEAD --` (that would wipe workflow state)."""
    porcelain = (
        " M .runtime/ai-dev-factory.sqlite\n"
        " M runs/.project-map.json\n"
    )

    calls: list[list[str]] = []
    state = {"first": True}

    def fake_run(args):
        calls.append(args)
        if args[:2] == ["git", "status"]:
            if state["first"]:
                state["first"] = False
                return _cp(stdout=porcelain)
            # After cleanup: project-map restored, sqlite still showing dirty
            return _cp(stdout=" M .runtime/ai-dev-factory.sqlite\n")
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        check_working_tree_clean()  # must not raise

    checkout_paths = [a[-1] for a in calls if a[:3] == ["git", "checkout", "HEAD"]]
    assert "runs/.project-map.json" in checkout_paths
    assert ".runtime/ai-dev-factory.sqlite" not in checkout_paths
    assert "intake preflight: clean enough to continue" in capsys.readouterr().out
