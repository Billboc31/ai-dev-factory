#!/usr/bin/env python3
"""Conflict resolver executor for ai-dev-factory.

Runs inside the ticket worktree:
1. Fetches origin and rebases onto origin/main.
2. On rebase conflict: collects context, invokes AI agent to edit files.
3. Loops until all conflicts cleared or MAX_RESOLVER_PASSES reached.
4. Stages only conflicted files per pass.
5. Runs tests.
6. Commits artifacts with message conflict(T{id}): resolve conflicts against main.
7. Pushes with --force-with-lease.
8. Transitions state to CONFLICT_RESOLVED_REVIEW_NEEDED (success)
   or CONFLICT_RESOLUTION_FAILED (any failure).
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

MAX_RESOLVER_PASSES = int(os.environ.get("CONFLICT_RESOLVER_MAX_PASSES", "3"))

ROOT = Path(__file__).resolve().parent
_RUN_STEP_PATH = ROOT / "run_step.py"
_CONTEXT_COLLECTOR_PATH = ROOT / "conflict_context_collector.py"

_rs_spec = importlib.util.spec_from_file_location("_run_step", _RUN_STEP_PATH)
_rs_mod = importlib.util.module_from_spec(_rs_spec)  # type: ignore[arg-type]
_rs_spec.loader.exec_module(_rs_mod)  # type: ignore[union-attr]
execute_external_command = _rs_mod.execute_external_command
compose_runtime_prompt = _rs_mod.compose_runtime_prompt
del _rs_spec, _rs_mod

_cc_spec = importlib.util.spec_from_file_location("_cc", _CONTEXT_COLLECTOR_PATH)
_cc_mod = importlib.util.module_from_spec(_cc_spec)  # type: ignore[arg-type]
_cc_spec.loader.exec_module(_cc_mod)  # type: ignore[union-attr]
collect_context = _cc_mod.collect_context
del _cc_spec, _cc_mod


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(ticket_id: str, message: str) -> None:
    log_path = Path("runs") / ticket_id / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] conflict-resolver: {message}\n")


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        args, text=True, capture_output=True, check=False, cwd=cwd, env=env
    )


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return _run(["git"] + args)


def _transition_state(ticket_id: str, run_dir: Path, new_state: str) -> None:
    state_file = run_dir / "state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["state"] = new_state
    data["updated_at"] = _now_iso()
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(state_file)
    _log(ticket_id, f"state → {new_state}")


def _write_error_log(run_dir: Path, message: str, stderr: str = "") -> None:
    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    error_path = conflict_dir / "error.log"
    content = f"[{_now_iso()}] {message}\n"
    if stderr.strip():
        content += f"\n--- stderr ---\n{stderr.strip()}\n"
    with error_path.open("a", encoding="utf-8") as fh:
        fh.write(content)


def _get_current_branch() -> str:
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("failed to determine current git branch")
    return result.stdout.strip()


def _list_conflicted_files() -> list[str]:
    result = _run_git(["diff", "--name-only", "--diff-filter=U"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _has_conflict_markers(path: str) -> bool:
    try:
        return "<<<<<<< " in Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _abort_rebase(ticket_id: str) -> None:
    _log(ticket_id, "aborting rebase")
    _run_git(["rebase", "--abort"])


def _run_tests(ticket_id: str, run_dir: Path) -> str:
    """Run pytest and return output text for the test report."""
    tests_dir = Path("tests")
    if not tests_dir.exists():
        return "No tests/ directory found — skipped.\n"

    result = _run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
    )
    lines = [
        f"# Test Report — conflict resolution for {ticket_id}",
        f"Generated at: {_now_iso()}",
        f"Exit code: {result.returncode}",
        "",
        "## Output",
        "",
        result.stdout or "(no stdout)",
    ]
    if result.stderr.strip():
        lines += ["", "## Stderr", "", result.stderr.strip()]

    return "\n".join(lines) + "\n"


def resolve_conflicts(ticket_id: str, exec_cmd: str) -> int:
    run_dir = Path("runs") / ticket_id
    state_file = run_dir / "state.json"

    if not state_file.exists():
        print(f"error: state.json not found for {ticket_id}", file=sys.stderr)
        return 2

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"error: state.json unreadable: {exc}", file=sys.stderr)
        return 2

    branch = data.get("branch", "")
    _log(ticket_id, f"start branch={branch}")

    # Safety guard: never run on main
    try:
        current_branch = _get_current_branch()
    except RuntimeError as exc:
        _log(ticket_id, f"failed to read branch: {exc}")
        _write_error_log(run_dir, str(exc))
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    if current_branch == "main":
        msg = "safety: refusing to resolve conflicts on 'main' branch"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    # Verify branch matches state
    if branch and current_branch != branch:
        msg = f"branch mismatch: current={current_branch!r} state={branch!r}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)

    # 1. fetch origin
    _log(ticket_id, "git fetch origin")
    fetch = _run_git(["fetch", "origin"])
    if fetch.returncode != 0:
        msg = f"git fetch failed: {fetch.stderr.strip()}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg, fetch.stderr)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    # 2. git rebase origin/main
    _log(ticket_id, "git rebase origin/main")
    rebase = _run_git(["rebase", "origin/main"])
    _log(ticket_id, f"rebase exit={rebase.returncode}")

    if rebase.returncode != 0:
        # Confirm actual conflict markers exist before invoking AI
        conflicted_files = _list_conflicted_files()
        if not conflicted_files:
            msg = f"rebase failed with no conflict markers: {rebase.stderr.strip()}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg, rebase.stderr)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            return 2

        _log(ticket_id, f"conflicts detected: {conflicted_files}")

        prompt_path = Path("prompts") / "generic" / "conflict-resolver.md"
        if not prompt_path.exists():
            msg = f"prompt not found: {prompt_path}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            return 2

        pass_count = 0
        while conflicted_files and pass_count < MAX_RESOLVER_PASSES:
            pass_count += 1
            pass_conflicted = list(conflicted_files)
            _log(ticket_id, f"[pass {pass_count}/{MAX_RESOLVER_PASSES}] start conflicted={pass_conflicted}")

            # Collect context after conflict markers exist on disk
            try:
                context_path = collect_context(ticket_id, conflicted_files=pass_conflicted)
                _log(ticket_id, f"context written: {context_path}")
            except Exception as exc:
                _log(ticket_id, f"context collection failed pass {pass_count}: {exc}")
                _write_error_log(run_dir, f"context collection failed: {exc}")
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
                return 2

            context_content = context_path.read_text(encoding="utf-8")
            task_content = prompt_path.read_text(encoding="utf-8") + "\n\n" + context_content
            runtime_prompt = compose_runtime_prompt(ticket_id, "conflict-resolver", task_content)

            # Snapshot the prompt
            prompts_dir = run_dir / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            existing = list(prompts_dir.glob("conflict-resolver-attempt-*.md"))
            attempt_num = len(existing) + 1
            snapshot = prompts_dir / f"conflict-resolver-attempt-{attempt_num}.md"
            snapshot.write_text(runtime_prompt, encoding="utf-8")
            _log(ticket_id, f"prompt snapshot: {snapshot}")

            _log(ticket_id, f"invoking AI resolver pass {pass_count}")
            stdout, stderr_ai, rc = execute_external_command(exec_cmd, runtime_prompt)

            if rc != 0:
                msg = f"AI resolver failed (rc={rc}) pass {pass_count}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, stderr_ai)
                (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
                return 2

            (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")

            # Check which files still have markers after AI edit (before staging)
            still_unresolved_markers = [f for f in pass_conflicted if _has_conflict_markers(f)]

            # Stage only the conflicted files (not git add -A)
            staged = list(pass_conflicted)
            add = _run_git(["add", "--"] + staged)
            if add.returncode != 0:
                msg = f"git add failed: {add.stderr.strip()}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, add.stderr)
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
                return 2

            # git rebase --continue
            env = dict(os.environ)
            env["GIT_EDITOR"] = "true"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            continue_result = subprocess.run(
                ["git", "rebase", "--continue"],
                text=True, capture_output=True, check=False, env=env,
            )
            continue_rc = continue_result.returncode

            if continue_rc != 0:
                out_lower = (continue_result.stdout + continue_result.stderr).lower()
                if "nothing to commit" in out_lower or "no changes" in out_lower:
                    _run_git(["rebase", "--skip"])
                    _log(ticket_id, "rebase --skip (nothing to commit)")
                    conflicted_files = _list_conflicted_files()
                else:
                    # Check if new conflicts appeared from the next commit in the rebase stack
                    new_conflicted = _list_conflicted_files()
                    if new_conflicted:
                        _log(ticket_id, (
                            f"[pass {pass_count}/{MAX_RESOLVER_PASSES}]"
                            f" conflicted={pass_conflicted}"
                            f" | staged={staged}"
                            f" | unresolved={still_unresolved_markers}"
                            f" | continue_rc={continue_rc}"
                        ))
                        conflicted_files = new_conflicted
                        continue
                    else:
                        msg = f"rebase --continue failed (pass {pass_count}): {continue_result.stderr.strip()}"
                        _log(ticket_id, msg)
                        _write_error_log(run_dir, msg, continue_result.stderr)
                        _abort_rebase(ticket_id)
                        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
                        return 2
            else:
                # Successful continue — check for conflicts from the next commit
                conflicted_files = _list_conflicted_files()

            _log(ticket_id, (
                f"[pass {pass_count}/{MAX_RESOLVER_PASSES}]"
                f" conflicted={pass_conflicted}"
                f" | staged={staged}"
                f" | unresolved={still_unresolved_markers}"
                f" | continue_rc={continue_rc}"
            ))

        if conflicted_files:
            msg = (
                f"conflicts remain after {pass_count}/{MAX_RESOLVER_PASSES} passes:"
                f" {conflicted_files}"
            )
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            return 2

        _log(ticket_id, f"all conflicts resolved after {pass_count} pass(es)")

    else:
        # Clean rebase — write resolution.md noting no conflicts needed
        res_path = conflict_dir / "resolution.md"
        if not res_path.exists():
            res_path.write_text(
                f"# Resolution — {ticket_id}\n\n"
                f"Rebase onto origin/main completed with no conflicts.\n"
                f"Generated at: {_now_iso()}\n",
                encoding="utf-8",
            )
        _log(ticket_id, "rebase clean — no conflicts")

    # 3. run tests
    _log(ticket_id, "running tests")
    test_report = _run_tests(ticket_id, run_dir)
    test_report_path = conflict_dir / "test-report.md"
    test_report_path.write_text(test_report, encoding="utf-8")
    _log(ticket_id, f"test-report written: {test_report_path}")

    if "Exit code: 0" not in test_report and "skipped" not in test_report.lower():
        msg = "tests failed after conflict resolution"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    # 4. commit all artifacts
    _log(ticket_id, "staging and committing resolution artifacts")
    add_all = _run_git(["add", "-A"])
    if add_all.returncode != 0:
        _log(ticket_id, f"git add before commit failed: {add_all.stderr.strip()}")

    commit_msg = f"conflict({ticket_id}): resolve conflicts against main"
    commit = _run_git(["commit", "-m", commit_msg])
    if commit.returncode != 0:
        out = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in out:
            _log(ticket_id, "nothing to commit after resolution")
        else:
            msg = f"commit failed: {commit.stderr.strip()}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg, commit.stderr)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            return 2
    else:
        sha_result = _run_git(["rev-parse", "--short", "HEAD"])
        sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown"
        _log(ticket_id, f"commit: sha={sha}")

    # 5. push with --force-with-lease
    push_target = branch or current_branch
    _log(ticket_id, f"git push --force-with-lease origin {push_target}")
    push = _run_git(["push", "--force-with-lease", "origin", push_target])
    if push.returncode != 0:
        msg = f"push --force-with-lease failed: {push.stderr.strip()}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg, push.stderr)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
        return 2

    _log(ticket_id, "push succeeded")

    # 6. transition only after clean rebase + passing tests
    _transition_state(ticket_id, run_dir, "CONFLICT_RESOLVED_REVIEW_NEEDED")
    _log(ticket_id, "done → CONFLICT_RESOLVED_REVIEW_NEEDED")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conflict resolver executor")
    parser.add_argument("ticket_id")
    parser.add_argument("--exec-cmd", required=True, help="AI runtime command")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return resolve_conflicts(args.ticket_id, args.exec_cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
