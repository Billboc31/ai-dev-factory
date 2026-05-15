#!/usr/bin/env python3
"""Local workflow daemon for ai-dev-factory.

Polls runs/*/state.json and launches run_ticket.py --auto for auto-runnable states.
Never bypasses human gate states.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_TICKET = ROOT / "run_ticket.py"
RUN_ISSUE_INTAKE = ROOT / "run_issue_intake.py"
ISSUE_INDEX_FILENAME = ".issue-intake.json"
RETRY_STATE_FILENAME = "retry-state.json"

AUTO_RUNNABLE_STATES = frozenset({
    "INIT",
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_APPROVED",
    "PLAN_FIX_REQUIRED",
    "IMPLEMENTATION_FIX_REQUIRED",
})

HUMAN_GATE_STATES = frozenset({
    "PLAN_REVIEW_NEEDED",
    "TEST_COMPLETE",
})

# Retry/cooldown policies per failure class.
# Keys match the categories produced by classify_runtime_failure in run_step.py.
_RETRY_POLICIES: dict[str, dict] = {
    "quota_exceeded":          {"action": "cooldown",    "cooldown_seconds": 3600},
    "provider_error":          {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_crashed":         {"action": "exponential", "base_seconds": 60, "max_retries": 5, "fallback_cooldown_seconds": 3600},
    "process_failed":          {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    "empty_output":            {"action": "fixed_delay", "delay_seconds": 300, "max_retries": 3},
    "write_permission_missing": {"action": "stop"},
    "unknown":                 {"action": "stop"},
}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(message: str) -> None:
    print(f"[{_now_iso()}] [daemon] {message}", flush=True)


def _lock_path(run_dir: Path) -> Path:
    return run_dir / "daemon.lock"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(run_dir: Path) -> bool:
    """Try to acquire daemon.lock. Returns True if acquired, False if held by a live process."""
    lock = _lock_path(run_dir)
    if lock.exists():
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if isinstance(pid, int) and _is_pid_alive(pid):
                return False
            _log(f"cleaning stale lock for {run_dir.name} (pid={pid})")
            lock.unlink()
        except (json.JSONDecodeError, OSError):
            try:
                lock.unlink()
            except OSError:
                pass
    try:
        lock.write_text(
            json.dumps({"pid": os.getpid(), "created_at": _now_iso()}),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def _release_lock(run_dir: Path) -> None:
    try:
        _lock_path(run_dir).unlink()
    except OSError:
        pass


# ── retry / cooldown state ────────────────────────────────────────────────────

def _retry_state_path(run_dir: Path) -> Path:
    return run_dir / RETRY_STATE_FILENAME


def _load_retry_state(run_dir: Path) -> dict:
    path = _retry_state_path(run_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_retry_state(run_dir: Path, state: dict) -> None:
    path = _retry_state_path(run_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def _clear_retry_state(run_dir: Path) -> None:
    try:
        _retry_state_path(run_dir).unlink()
    except OSError:
        pass


def _read_last_failure_class(run_dir: Path) -> str | None:
    """Return the last failure class logged in runtime.log, or None."""
    log_path = run_dir / "runtime.log"
    if not log_path.exists():
        return None
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return None
    last_class = None
    for line in content.splitlines():
        m = re.search(r"runtime failure: (\w+)", line)
        if m:
            last_class = m.group(1)
    return last_class


def _cooldown_until(seconds: int) -> str:
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
    return until.strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply_retry_policy(ticket_id: str, failure_class: str, retry_state: dict) -> dict:
    """Return an updated retry_state dict after applying the policy for failure_class."""
    policy = _RETRY_POLICIES.get(failure_class, {"action": "stop"})
    action = policy["action"]
    new_state: dict = dict(retry_state)
    new_state["failure_class"] = failure_class
    new_state.setdefault("retry_count", 0)

    if action == "stop":
        new_state["stopped"] = True
        new_state["stop_reason"] = failure_class
        _log(f"{ticket_id}: retry policy=stop failure={failure_class} — requires human attention")

    elif action == "cooldown":
        seconds = policy["cooldown_seconds"]
        new_state["cooldown_until"] = _cooldown_until(seconds)
        new_state.pop("stopped", None)
        _log(f"{ticket_id}: retry policy=cooldown failure={failure_class} cooldown={seconds}s until={new_state['cooldown_until']}")

    elif action == "exponential":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            fallback = policy["fallback_cooldown_seconds"]
            new_state["cooldown_until"] = _cooldown_until(fallback)
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} max_retries={max_retries} reached — cooldown {fallback}s")
        else:
            delay = policy["base_seconds"] * (2 ** count)
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=exponential failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    elif action == "fixed_delay":
        count = new_state["retry_count"]
        max_retries = policy["max_retries"]
        if count >= max_retries:
            new_state["stopped"] = True
            new_state["stop_reason"] = f"{failure_class}_max_retries"
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} max_retries={max_retries} reached — stopped")
        else:
            delay = policy["delay_seconds"]
            new_state["cooldown_until"] = _cooldown_until(delay)
            new_state["retry_count"] = count + 1
            new_state.pop("stopped", None)
            _log(f"{ticket_id}: retry policy=fixed_delay failure={failure_class} attempt={count + 1}/{max_retries} delay={delay}s")

    return new_state


def _is_blocked_by_retry(ticket_id: str, retry_state: dict) -> bool:
    """Return True and log if the ticket must be skipped due to retry/cooldown state."""
    if retry_state.get("stopped"):
        reason = retry_state.get("stop_reason", "unknown")
        _log(f"skipping {ticket_id}: stopped reason={reason} — requires human attention")
        return True
    cooldown_until = retry_state.get("cooldown_until")
    if cooldown_until:
        try:
            until_dt = datetime.datetime.strptime(cooldown_until, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < until_dt:
                remaining = int((until_dt - now).total_seconds())
                _log(f"skipping {ticket_id}: in cooldown until={cooldown_until} remaining={remaining}s")
                return True
        except ValueError:
            pass
    return False


# ── pre-flight dirty tree check ───────────────────────────────────────────────

# Mirrors COMMIT_SCOPE in run_ticket.py — files in these paths are auto-checkpointable
_CODE_SCOPE_PREFIXES: tuple[str, ...] = (
    "tools/",
    "tests/",
    "prompts/",
    "tickets/",
    "docs/",
    "ai/",
    "services/",
    "apps/",
    "README.md",
    ".gitignore",
    "package.json",
    "package-lock.json",
)


def _classify_dirty_files(ticket_id: str) -> tuple[list[str], list[str], list[str]]:
    """Run git status and classify dirty files into three buckets.

    Returns (workflow_artifacts, code_scope_files, unknown_files).
    - workflow_artifacts: files under runs/ — auto-checkpointable
    - code_scope_files: files in COMMIT_SCOPE — auto-checkpointable with --include-code
    - unknown_files: anything else — trigger safe abort
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    workflow_artifacts: list[str] = []
    code_scope_files: list[str] = []
    unknown_files: list[str] = []
    if result.returncode != 0:
        return workflow_artifacts, code_scope_files, unknown_files
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if path.startswith("runs/"):
            workflow_artifacts.append(path)
        elif any(path.startswith(p) for p in _CODE_SCOPE_PREFIXES):
            code_scope_files.append(path)
        else:
            unknown_files.append(path)
    return workflow_artifacts, code_scope_files, unknown_files


def _ensure_clean_working_tree(ticket_id: str, auto_push: bool = False) -> bool:
    """Ensure working tree is clean before launching a ticket step.

    If dirty files are workflow artifacts or code-scope files → automatic checkpoint commit.
    If any unknown files are dirty → abort safely.
    Returns True if ready to proceed, False to abort.
    """
    workflow_artifacts, code_scope_files, unknown_files = _classify_dirty_files(ticket_id)

    if not workflow_artifacts and not code_scope_files and not unknown_files:
        return True

    if unknown_files:
        _log(f"{ticket_id}: pre-flight abort — unknown dirty files: {unknown_files!r}")
        _log(f"{ticket_id}: pre-flight abort — commit or stash unknown files before daemon can proceed")
        return False

    if code_scope_files:
        _log(f"{ticket_id}: pre-flight — dirty code-scope files detected: {code_scope_files!r}")
    _log(f"{ticket_id}: pre-flight — triggering checkpoint commit (--include-code)")
    commit_result = subprocess.run(
        [sys.executable, str(RUN_TICKET), ticket_id, "--commit", "--include-code"],
        capture_output=True, text=True, check=False,
    )
    for line in commit_result.stdout.splitlines():
        _log(f"{ticket_id}: {line}")
    for line in commit_result.stderr.splitlines():
        _log(f"{ticket_id} [err]: {line}")

    if commit_result.returncode not in (0, 1):
        _log(f"{ticket_id}: pre-flight abort — checkpoint commit failed rc={commit_result.returncode}")
        return False

    if commit_result.returncode == 0:
        _log(f"checkpoint commit for {ticket_id}")
        if auto_push:
            push_result = subprocess.run(
                [sys.executable, str(RUN_TICKET), ticket_id, "--push"],
                capture_output=True, text=True, check=False,
            )
            for line in push_result.stdout.splitlines():
                _log(f"{ticket_id}: {line}")
            if push_result.returncode == 0:
                _log(f"checkpoint push for {ticket_id}")
            else:
                _log(f"{ticket_id}: checkpoint push failed rc={push_result.returncode}")

    return True


def _commit_after_intake(ticket_id: str) -> None:
    """Commit runs/ + COMMIT_SCOPE after issue intake to include .issue-intake.json."""
    _log(f"checkpoint commit for {ticket_id}")
    result = subprocess.run(
        [sys.executable, str(RUN_TICKET), ticket_id, "--commit", "--include-code"],
        capture_output=True, text=True, check=False,
    )
    for line in result.stdout.splitlines():
        _log(f"{ticket_id}: {line}")
    for line in result.stderr.splitlines():
        _log(f"{ticket_id} [err]: {line}")
    if result.returncode == 0:
        _log(f"bootstrap checkpoint completed for {ticket_id}")
    elif result.returncode == 1:
        _log(f"{ticket_id}: nothing new to commit after intake")
    else:
        _log(f"{ticket_id}: intake checkpoint commit failed rc={result.returncode}")


# ── state json helpers ────────────────────────────────────────────────────────

def _load_state_json(run_dir: Path) -> dict:
    path = run_dir / "state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state_json(run_dir: Path, data: dict) -> None:
    path = run_dir / "state.json"
    updated = {**data, "updated_at": _now_iso()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    tmp.replace(path)


# ── PR lifecycle ──────────────────────────────────────────────────────────────

def _pr_title(ticket_id: str, run_dir: Path) -> str:
    ticket_path = run_dir / "ticket.md"
    if ticket_path.exists():
        for line in ticket_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return f"{ticket_id} — workflow complete"


def _pr_body(ticket_id: str, issue_number: int | None) -> str:
    lines = [
        f"## {ticket_id}",
        "",
        "Workflow reached `TEST_COMPLETE`.",
        "",
        "### Gates",
        "- [x] PLAN_APPROVED",
        "- [x] IMPLEMENTATION_APPROVED",
        "- [ ] MEMORY_APPROVED",
    ]
    if issue_number:
        lines += ["", f"Closes #{issue_number}"]
    return "\n".join(lines)


def create_or_update_pr(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Create or update the GitHub PR for a ticket at TEST_COMPLETE. Non-blocking on gh failure."""
    state = _load_state_json(run_dir)
    branch = state.get("branch")
    issue_number = state.get("issue_number")
    pr_number = state.get("pr_number")

    if not branch:
        _log(f"{ticket_id}: create_or_update_pr: no branch in state — skipping")
        return

    # Skip if PR body is already synced to avoid repeated gh pr edit calls
    if pr_number is not None and state.get("pr_synced"):
        return

    title = _pr_title(ticket_id, run_dir)
    body = _pr_body(ticket_id, issue_number)

    if pr_number is None:
        list_cmd = ["gh", "pr", "list", "--head", branch, "--json", "number", "--state", "open"]
        if repo:
            list_cmd += ["--repo", repo]
        try:
            list_result = subprocess.run(list_cmd, capture_output=True, text=True, check=False)
            if list_result.returncode == 0 and list_result.stdout.strip():
                existing = json.loads(list_result.stdout)
                if existing:
                    pr_number = existing[0]["number"]
                    _log(f"{ticket_id}: found existing PR #{pr_number} — will update")
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            _log(f"{ticket_id}: gh pr list failed — proceeding with create")

    if pr_number is not None:
        edit_cmd = ["gh", "pr", "edit", str(pr_number), "--body", body]
        if repo:
            edit_cmd += ["--repo", repo]
        try:
            result = subprocess.run(edit_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                state["pr_synced"] = True
                _save_state_json(run_dir, state)
                _log(f"{ticket_id}: PR #{pr_number} updated")
            else:
                _log(f"{ticket_id}: gh pr edit failed (rc={result.returncode}): {result.stderr.strip()}")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot update PR #{pr_number}")
    else:
        create_cmd = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        if repo:
            create_cmd += ["--repo", repo]
        try:
            result = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                m = re.search(r"/pull/(\d+)", pr_url)
                if m:
                    pr_number = int(m.group(1))
                    state["pr_number"] = pr_number
                    state["pr_synced"] = True
                    _save_state_json(run_dir, state)
                    _log(f"{ticket_id}: PR #{pr_number} created: {pr_url}")
                else:
                    _log(f"{ticket_id}: PR created but number not parsed from: {pr_url!r}")
            else:
                stderr = result.stderr.strip()
                _log(f"{ticket_id}: gh pr create failed (rc={result.returncode}): {stderr}")
                if "No commits between" in stderr:
                    state["pr_skipped_no_diff"] = True
                    state["daemon_archived"] = True
                    _save_state_json(run_dir, state)
                    _log(f"{ticket_id}: no diff — marked pr_skipped_no_diff=true daemon_archived=true")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot create PR")


def check_and_close_issue(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Detect merged PR, close the source issue, and remove ai-ready label. Non-blocking."""
    state = _load_state_json(run_dir)

    # Skip if already handled to avoid repeated gh calls on every daemon cycle
    if state.get("issue_closed"):
        return

    pr_number = state.get("pr_number")
    issue_number = state.get("issue_number")

    if not pr_number:
        return

    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "state"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"{ticket_id}: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
            return
        pr_data = json.loads(result.stdout)
    except (json.JSONDecodeError, FileNotFoundError):
        _log(f"{ticket_id}: gh pr view failed or gh not found")
        return

    if pr_data.get("state") != "MERGED":
        return

    _log(f"{ticket_id}: PR #{pr_number} merged — handling issue closure")

    if not issue_number:
        return

    close_cmd = ["gh", "issue", "close", str(issue_number)]
    if repo:
        close_cmd += ["--repo", repo]
    try:
        close_result = subprocess.run(close_cmd, capture_output=True, text=True, check=False)
        if close_result.returncode == 0:
            _log(f"{ticket_id}: issue #{issue_number} closed")
        else:
            _log(f"{ticket_id}: gh issue close failed (rc={close_result.returncode}): {close_result.stderr.strip()}")
    except FileNotFoundError:
        _log(f"{ticket_id}: gh not found — cannot close issue #{issue_number}")

    label_cmd = ["gh", "issue", "edit", str(issue_number), "--remove-label", "ai-ready"]
    if repo:
        label_cmd += ["--repo", repo]
    try:
        label_result = subprocess.run(label_cmd, capture_output=True, text=True, check=False)
        if label_result.returncode == 0:
            _log(f"{ticket_id}: label 'ai-ready' removed from issue #{issue_number}")
        else:
            _log(f"{ticket_id}: gh issue edit label failed (rc={label_result.returncode}): {label_result.stderr.strip()}")
    except FileNotFoundError:
        _log(f"{ticket_id}: gh not found — cannot remove label from issue #{issue_number}")

    # Persist so we don't repeat close/label-removal on subsequent daemon cycles
    state["issue_closed"] = True
    _save_state_json(run_dir, state)


def _checkpoint_and_push_before_pr(ticket_id: str) -> bool:
    """Checkpoint commit + push before PR creation. Returns False if commit or push failed."""
    _log(f"{ticket_id}: pre-PR checkpoint commit")
    commit_result = subprocess.run(
        [sys.executable, str(RUN_TICKET), ticket_id, "--commit", "--include-code"],
        capture_output=True, text=True, check=False,
    )
    for line in commit_result.stdout.splitlines():
        _log(f"{ticket_id}: {line}")
    for line in commit_result.stderr.splitlines():
        _log(f"{ticket_id} [err]: {line}")
    if commit_result.returncode not in (0, 1):
        _log(f"{ticket_id}: pre-PR checkpoint failed rc={commit_result.returncode}")
        return False
    if commit_result.returncode == 0:
        _log(f"{ticket_id}: pre-PR checkpoint committed — pushing")
        push_result = subprocess.run(
            [sys.executable, str(RUN_TICKET), ticket_id, "--push"],
            capture_output=True, text=True, check=False,
        )
        for line in push_result.stdout.splitlines():
            _log(f"{ticket_id}: {line}")
        if push_result.returncode != 0:
            _log(f"{ticket_id}: pre-PR push failed rc={push_result.returncode}")
            return False
        _log(f"{ticket_id}: pre-PR push ok")
    else:
        _log(f"{ticket_id}: pre-PR checkpoint — nothing to commit, skipping push")
    return True


def handle_test_complete(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Orchestrate PR lifecycle for a ticket at TEST_COMPLETE."""
    _log(f"{ticket_id}: TEST_COMPLETE PR lifecycle")
    if not _checkpoint_and_push_before_pr(ticket_id):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(ticket_id, run_dir, repo)
    check_and_close_issue(ticket_id, run_dir, repo)


def scan_tickets(runs_dir: Path) -> list[tuple[str, str]]:
    """Return (ticket_id, state) for all readable state.json files, sorted by ticket_id."""
    results = []
    for state_path in sorted(runs_dir.glob("*/state.json")):
        ticket_id = state_path.parent.name
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            if data.get("daemon_archived"):
                _log(f"skipping {ticket_id}: daemon_archived=true")
                continue
            state = data.get("state", "")
            if state:
                results.append((ticket_id, state))
        except (json.JSONDecodeError, OSError):
            _log(f"skipping {ticket_id}: corrupted or unreadable state.json")
    return results


def build_run_ticket_command(
    ticket_id: str,
    exec_cmd: str | None,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
) -> list[str]:
    """Build the run_ticket.py command list. exec_cmd is passed as a single string element."""
    cmd = [sys.executable, str(RUN_TICKET), ticket_id, "--auto"]
    if exec_cmd:
        cmd.extend(["--exec-cmd", exec_cmd])
    if auto_commit:
        cmd.append("--auto-commit")
    if auto_push:
        cmd.append("--auto-push")
    if auto_include_code:
        cmd.append("--auto-include-code")
    return cmd


def launch_ticket(
    ticket_id: str,
    exec_cmd: str,
    dry_run: bool,
    runs_dir: Path,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
) -> None:
    """Launch run_ticket.py --auto for one ticket. No-op in dry_run mode."""
    run_dir = runs_dir / ticket_id

    if dry_run:
        _log(f"dry-run: would launch {ticket_id} --auto --exec-cmd {exec_cmd!r}")
        return

    if not _acquire_lock(run_dir):
        _log(f"skipping {ticket_id}: already running (lock held)")
        return

    try:
        if not _ensure_clean_working_tree(ticket_id, auto_push=auto_push):
            return

        cmd = build_run_ticket_command(ticket_id, exec_cmd, auto_commit, auto_push, auto_include_code)
        _log(f"Running ticket command: {shlex.join(cmd)}")
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            _log(f"{ticket_id}: {line}")
        for line in result.stderr.splitlines():
            _log(f"{ticket_id} [err]: {line}")
        _log(f"{ticket_id}: done rc={result.returncode}")
        if result.returncode != 0:
            failure_class = _read_last_failure_class(run_dir)
            if failure_class:
                retry_state = _load_retry_state(run_dir)
                retry_state = _apply_retry_policy(ticket_id, failure_class, retry_state)
                _save_retry_state(run_dir, retry_state)
            else:
                _log(f"{ticket_id}: no failure class in runtime.log — retry policy not applied")
        else:
            _clear_retry_state(run_dir)
    finally:
        _release_lock(run_dir)


# ── issue polling ─────────────────────────────────────────────────────────────

def _sync_main_before_intake() -> bool:
    """Checkout main and pull before issue intake. Returns True if ready to proceed."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        _log("sync-main: git status failed — aborting intake")
        return False
    unknown_files = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if not path.startswith("runs/") and not any(path.startswith(p) for p in _CODE_SCOPE_PREFIXES):
            unknown_files.append(path)
    if unknown_files:
        _log(f"sync-main: unknown dirty files detected — aborting intake: {unknown_files!r}")
        return False
    _log("syncing main before issue intake")
    checkout = subprocess.run(
        ["git", "checkout", "main"],
        capture_output=True, text=True, check=False,
    )
    if checkout.returncode != 0:
        _log(f"sync-main: git checkout main failed (rc={checkout.returncode}): {checkout.stderr.strip()}")
        return False
    _log("checkout main completed")
    pull = subprocess.run(
        ["git", "pull", "origin", "main"],
        capture_output=True, text=True, check=False,
    )
    if pull.returncode != 0:
        _log(f"sync-main: git pull origin main failed (rc={pull.returncode}): {pull.stderr.strip()}")
        return False
    _log("pull origin main completed")
    return True


def _count_active_tickets(runs_dir: Path) -> int:
    """Count non-archived, non-closed tickets with a state."""
    count = 0
    for state_path in runs_dir.glob("*/state.json"):
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("daemon_archived") or data.get("issue_closed"):
            continue
        if data.get("state"):
            count += 1
    return count


def load_issue_index(runs_dir: Path) -> dict[str, str]:
    """Load the anti-duplicate index mapping issue numbers to ticket IDs."""
    path = runs_dir / ISSUE_INDEX_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_issue_index(runs_dir: Path, index: dict[str, str]) -> None:
    """Persist the anti-duplicate index atomically via a temp file rename."""
    path = runs_dir / ISSUE_INDEX_FILENAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=2), encoding="utf-8")
    tmp.replace(path)


def next_ticket_id(runs_dir: Path, reserved: set[str] | None = None) -> str:
    """Compute the next available ticket ID by scanning runs/T*/ and the optional reserved set."""
    max_num = 0
    for p in runs_dir.glob("T*/"):
        m = re.match(r"T(\d+)$", p.name)
        if m:
            max_num = max(max_num, int(m.group(1)))
    for tid in (reserved or ()):
        m = re.match(r"T(\d+)$", tid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"T{max_num + 1:03d}"


def slugify_title(title: str) -> str:
    """Convert an issue title to a URL-safe branch slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:50].rstrip("-")
    return slug or "issue"


def fetch_ready_issues(label: str, repo: str | None) -> list[dict]:
    """Call `gh issue list` and return open issues with the given label. Returns [] on any failure."""
    cmd = ["gh", "issue", "list", "--label", label, "--json", "number,title", "--state", "open"]
    if repo:
        cmd += ["--repo", repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"gh issue list failed (rc={result.returncode}) — skipping issue polling")
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except FileNotFoundError:
        _log("gh not found — skipping issue polling")
        return []
    except json.JSONDecodeError:
        _log("gh returned invalid JSON — skipping issue polling")
        return []


def call_issue_intake(issue_number: int, ticket_id: str, branch_slug: str, repo: str | None, push: bool = False) -> bool:
    """Run run_issue_intake.py for one issue. Returns True on success."""
    cmd = [
        sys.executable, str(RUN_ISSUE_INTAKE),
        "--issue", str(issue_number),
        "--ticket-id", ticket_id,
        "--branch-slug", branch_slug,
    ]
    if repo:
        cmd += ["--repo", repo]
    if push:
        cmd.append("--push")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        _log(f"intake {ticket_id}: {line}")
    for line in result.stderr.splitlines():
        _log(f"intake {ticket_id} [err]: {line}")
    return result.returncode == 0


def poll_github_issues(
    runs_dir: Path,
    label: str,
    repo: str | None,
    max_active_tickets: int = 1,
) -> None:
    """Detect ready GitHub issues and create local runs for new ones."""
    issues = fetch_ready_issues(label, repo)
    if not issues:
        _log(f"no issues found with label={label!r}")
        return

    index = load_issue_index(runs_dir)
    candidates = sorted(
        [i for i in issues if str(i["number"]) not in index],
        key=lambda i: i["number"],
    )
    already_ingested = [i for i in issues if str(i["number"]) in index]
    for issue in already_ingested:
        _log(f"issue #{issue['number']} already ingested as {index[str(issue['number'])]} — skipping")

    if not candidates:
        _log(f"found {len(issues)} issue(s) with label={label!r} — all already ingested")
        return

    active = _count_active_tickets(runs_dir)
    _log(f"found {len(candidates)} candidate issue(s) active_tickets={active} max_active_tickets={max_active_tickets}")

    if active >= max_active_tickets:
        for issue in candidates:
            _log(f"issue #{issue['number']} ({issue.get('title', '')!r}) skipped-for-capacity active={active} max={max_active_tickets}")
        return

    issue = candidates[0]
    for skipped in candidates[1:]:
        _log(f"issue #{skipped['number']} ({skipped.get('title', '')!r}) queued — capacity reserved for issue #{issue['number']}")

    number = str(issue["number"])
    title = issue.get("title", "")
    ticket_id = next_ticket_id(runs_dir, reserved=set(index.values()))
    slug = slugify_title(title)
    _log(f"ingesting issue #{number} ({title!r}) as {ticket_id} slug={slug!r}")

    if not _sync_main_before_intake():
        _log("issue intake aborted — git sync failed")
        return

    if call_issue_intake(int(number), ticket_id, slug, repo, push=True):
        index[number] = ticket_id
        save_issue_index(runs_dir, index)
        _log(f"issue #{number} ingested as {ticket_id}")
        _commit_after_intake(ticket_id)
    else:
        _log(f"intake failed for issue #{number} — will retry next cycle")


def run_once(
    exec_cmd: str,
    dry_run: bool,
    runs_dir: Path,
    auto_commit: bool = False,
    auto_push: bool = False,
    auto_include_code: bool = False,
    repo: str | None = None,
) -> None:
    """Scan all tickets and process auto-runnable ones."""
    tickets = scan_tickets(runs_dir)
    if not tickets:
        _log("no tickets found")
        return
    for ticket_id, state in tickets:
        if state in AUTO_RUNNABLE_STATES:
            _log(f"detected {ticket_id} state={state}")
            run_dir = runs_dir / ticket_id
            retry_state = _load_retry_state(run_dir)
            if _is_blocked_by_retry(ticket_id, retry_state):
                continue
            launch_ticket(ticket_id, exec_cmd, dry_run, runs_dir, auto_commit=auto_commit, auto_push=auto_push, auto_include_code=auto_include_code)
        elif state == "TEST_COMPLETE":
            run_dir = runs_dir / ticket_id
            ticket_state = _load_state_json(run_dir)
            if ticket_state.get("issue_closed") or ticket_state.get("pr_skipped_no_diff"):
                _log(f"skipping {ticket_id}: TEST_COMPLETE already finalized")
                continue
            _log(f"detected {ticket_id} state=TEST_COMPLETE (human gate — PR lifecycle)")
            if not dry_run:
                handle_test_complete(ticket_id, run_dir, repo)
            else:
                _log(f"dry-run: would handle {ticket_id} TEST_COMPLETE PR lifecycle")
        elif state in HUMAN_GATE_STATES:
            _log(f"skipping {ticket_id} state={state} (human gate)")
        else:
            _log(f"skipping {ticket_id} state={state}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local workflow daemon for ai-dev-factory")
    parser.add_argument("--exec-cmd", required=True, help="Command passed to run_ticket.py --auto")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without executing")
    parser.add_argument("--runs-dir", default="runs", help="Path to runs directory (default: runs)")
    parser.add_argument("--poll-issues", action="store_true", help="Enable GitHub issue polling")
    parser.add_argument("--issue-label", default="ai-ready", help="GitHub label to filter issues (default: ai-ready)")
    parser.add_argument("--issue-repo", default=None, help="GitHub repo (owner/repo) — defaults to current repo")
    parser.add_argument("--auto-commit", action="store_true", help="After each successful step, commit runs/ artifacts")
    parser.add_argument("--auto-push", action="store_true", help="After each successful auto-commit, push the ticket branch")
    parser.add_argument("--auto-include-code", action="store_true", help="With --auto-commit, also stage COMMIT_SCOPE paths (tools/, tests/, prompts/, tickets/, docs/, ai/)")
    parser.add_argument("--max-active-tickets", type=int, default=1, help="Maximum active tickets before skipping issue intake (default: 1)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)

    if not runs_dir.exists():
        print(f"error: runs dir not found: {runs_dir}", file=sys.stderr)
        return 2

    _log(f"starting daemon exec-cmd={args.exec_cmd!r} interval={args.interval}s dry-run={args.dry_run}")
    if args.poll_issues:
        _log(f"issue polling enabled label={args.issue_label!r} repo={args.issue_repo!r} max-active-tickets={args.max_active_tickets}")
    if args.auto_commit:
        _log(f"auto-commit enabled auto-push={args.auto_push} auto-include-code={args.auto_include_code}")

    if args.once:
        if args.poll_issues:
            poll_github_issues(runs_dir, args.issue_label, args.issue_repo, max_active_tickets=args.max_active_tickets)
        run_once(args.exec_cmd, args.dry_run, runs_dir, auto_commit=args.auto_commit, auto_push=args.auto_push, auto_include_code=args.auto_include_code, repo=args.issue_repo)
        return 0

    try:
        while True:
            if args.poll_issues:
                poll_github_issues(runs_dir, args.issue_label, args.issue_repo, max_active_tickets=args.max_active_tickets)
            run_once(args.exec_cmd, args.dry_run, runs_dir, auto_commit=args.auto_commit, auto_push=args.auto_push, auto_include_code=args.auto_include_code, repo=args.issue_repo)
            _log(f"sleeping {args.interval}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        _log("interrupted — daemon stopping")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
