"""GitHub PR lifecycle for tickets that reached ``TEST_COMPLETE``.

Invoked at the end of the ``run_ticket.py`` workflow (after tester) and as a
daemon fallback for tickets that reached ``TEST_COMPLETE`` without finalizing.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent

_rc_spec = importlib.util.spec_from_file_location("_runtime_checkpoint", ROOT / "runtime_checkpoint.py")
_rc_mod = importlib.util.module_from_spec(_rc_spec)  # type: ignore[arg-type]
_rc_spec.loader.exec_module(_rc_mod)  # type: ignore[union-attr]
checkpoint_transition = _rc_mod.checkpoint_transition
CheckpointError = _rc_mod.CheckpointError
DirtyTreeError = _rc_mod.DirtyTreeError
del _rc_spec, _rc_mod

LogFn = Callable[[str], None]
_log_fn: LogFn | None = None


def configure_log(log: LogFn | None) -> None:
    """Optional sink (e.g. daemon ``_log``). Defaults to stderr."""
    global _log_fn
    _log_fn = log


def _log(message: str) -> None:
    if _log_fn is not None:
        _log_fn(message)
        return
    print(f"[pr-lifecycle] {message}", file=sys.stderr, flush=True)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _sync_runtime_db(
    ticket_id: str,
    run_dir: Path,
    *,
    worktree_cwd: str | None = None,
    repo: str | None = None,
) -> None:
    """Push ``state.json`` fields into ``ticket_runtime`` when a DB is configured."""
    try:
        import runtime_db as rdb

        db_path = rdb.get_db_path()
        if not db_path:
            return
        state_data = _load_state_json(run_dir)
        state = (state_data.get("state") or "").strip()
        if not state:
            return
        fields: dict = {
            "state": state,
            "branch": state_data.get("branch"),
            "issue_number": state_data.get("issue_number"),
            "run_dir": str(run_dir),
            "worktree_path": worktree_cwd,
            "daemon_archived": int(bool(state_data.get("daemon_archived"))),
            "pr_number": state_data.get("pr_number"),
        }
        pr_number = state_data.get("pr_number")
        if pr_number:
            try:
                from ticket_merge_state import fetch_github_pr_state_label

                gh_state = fetch_github_pr_state_label(
                    ROOT.parent.parent, int(pr_number), repo=repo
                )
                if gh_state:
                    fields["pr_state"] = gh_state
            except Exception:
                pass
        elif state_data.get("pr_merged"):
            fields["pr_state"] = "MERGED"
        rdb.upsert_ticket_runtime(db_path, ticket_id, **fields)
    except Exception as exc:
        _log(f"{ticket_id}: runtime DB sync failed: {exc}")


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

    if pr_number is None:
        prefix = f"ticket/{ticket_id}-"
        fallback_cmd = ["gh", "pr", "list", "--state", "open", "--json", "number,headRefName", "--limit", "100"]
        if repo:
            fallback_cmd += ["--repo", repo]
        try:
            fb_result = subprocess.run(fallback_cmd, capture_output=True, text=True, check=False)
            if fb_result.returncode == 0 and fb_result.stdout.strip():
                all_prs = json.loads(fb_result.stdout)
                matching = [
                    p for p in all_prs
                    if isinstance(p, dict) and str(p.get("headRefName", "")).startswith(prefix)
                ]
                if matching:
                    pr_number = matching[0]["number"]
                    head_ref = matching[0].get("headRefName", "")
                    _log(
                        f"{ticket_id}: found PR #{pr_number} via branch prefix {prefix!r} "
                        f"(headRef={head_ref!r}) — branch may have been renamed"
                    )
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            pass

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
                    _sync_runtime_db(ticket_id, run_dir, repo=repo)
                    _log(f"{ticket_id}: no diff — marked pr_skipped_no_diff=true daemon_archived=true")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot create PR")


def check_and_close_issue(ticket_id: str, run_dir: Path, repo: str | None) -> None:
    """Detect merged PR, close the source issue, and remove ai-ready label. Non-blocking."""
    state = _load_state_json(run_dir)

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

    state["issue_closed"] = True
    _save_state_json(run_dir, state)
    _sync_runtime_db(ticket_id, run_dir, repo=repo)


def _checkpoint_and_push_before_pr(ticket_id: str, cwd: str | None = None) -> bool:
    """Checkpoint commit + push before PR creation. Returns False if commit or push failed."""
    _log(f"{ticket_id}: pre-PR checkpoint commit")
    try:
        checkpoint_transition(
            ticket_id,
            f"{ticket_id}: checkpoint [TEST_COMPLETE] — update workflow artifacts",
            push=True,
            include_code=True,
            cwd=cwd,
        )
        _log(f"{ticket_id}: pre-PR push ok")
        return True
    except CheckpointError as exc:
        _log(f"{ticket_id}: pre-PR checkpoint failed: {exc}")
        return False
    except DirtyTreeError as exc:
        _log(f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — pre-PR: {exc}")
        return False


def auto_merge_pr(ticket_id: str, run_dir: Path, repo: str | None) -> bool:
    """Merge the ticket PR automatically if all guards pass. Returns True if merged."""
    state = _load_state_json(run_dir)
    pr_number = state.get("pr_number")

    if not pr_number:
        _log(f"{ticket_id}: auto-merge: no pr_number in state — skipping")
        return False

    if state.get("pr_merged"):
        _log(f"{ticket_id}: auto-merge: already merged — skipping")
        return False

    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "state,mergeable"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            _log(f"{ticket_id}: auto-merge: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
            return False
        pr_data = json.loads(result.stdout)
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False
    except json.JSONDecodeError:
        _log(f"{ticket_id}: auto-merge: invalid JSON from gh pr view")
        return False

    pr_state = pr_data.get("state")
    if pr_state == "MERGED":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} already merged — marking state")
        state["pr_merged"] = True
        state["daemon_archived"] = True
        _save_state_json(run_dir, state)
        _sync_runtime_db(ticket_id, run_dir, repo=repo)
        return True
    if pr_state != "OPEN":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} state={pr_state!r} — not OPEN, skipping")
        return False

    mergeable = pr_data.get("mergeable")
    if mergeable == "CONFLICTING":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} has conflicts — skipping")
        return False

    merge_cmd = ["gh", "pr", "merge", str(pr_number), "--squash", "--delete-branch"]
    if repo:
        merge_cmd += ["--repo", repo]
    try:
        merge_result = subprocess.run(merge_cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False

    if merge_result.returncode != 0:
        _log(f"{ticket_id}: auto-merge: gh pr merge failed (rc={merge_result.returncode}): {merge_result.stderr.strip()}")
        return False

    _log(f"{ticket_id}: auto-merge: PR #{pr_number} merged successfully")
    state["pr_merged"] = True
    state["daemon_archived"] = True
    _save_state_json(run_dir, state)
    _sync_runtime_db(ticket_id, run_dir, repo=repo)
    return True


def detect_pr_conflict(
    ticket_id: str,
    pr_number: int,
    run_dir: Path,
    repo: str | None = None,
) -> bool:
    """Return True and write conflict metadata to state.json if the PR is CONFLICTING."""
    check_cmd = ["gh", "pr", "view", str(pr_number), "--json", "mergeable"]
    if repo:
        check_cmd += ["--repo", repo]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        _log(f"{ticket_id}: conflict detection: gh not found")
        return False
    if result.returncode != 0:
        _log(f"{ticket_id}: conflict detection: gh pr view failed (rc={result.returncode}): {result.stderr.strip()}")
        return False
    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        _log(f"{ticket_id}: conflict detection: invalid JSON from gh pr view")
        return False

    if pr_data.get("mergeable") != "CONFLICTING":
        return False

    files_cmd = ["gh", "pr", "view", str(pr_number), "--json", "files"]
    if repo:
        files_cmd += ["--repo", repo]
    conflicted_files: list[str] = []
    try:
        files_result = subprocess.run(files_cmd, capture_output=True, text=True, check=False)
        if files_result.returncode == 0:
            files_data = json.loads(files_result.stdout)
            conflicted_files = [
                f["path"] for f in files_data.get("files", [])
                if isinstance(f, dict) and "path" in f
            ]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    state = _load_state_json(run_dir)
    pre_conflict_state = state.get("state", "")
    state["pre_conflict_state"] = pre_conflict_state
    state["conflict_detected_at"] = _now_iso()
    state["conflict_pr_number"] = pr_number
    state["conflicted_files"] = conflicted_files
    state["state"] = "CONFLICT_RESOLUTION_NEEDED"
    _save_state_json(run_dir, state)
    _log(
        f"{ticket_id}: PR #{pr_number} is CONFLICTING — transitioned to "
        f"CONFLICT_RESOLUTION_NEEDED (was {pre_conflict_state!r}, {len(conflicted_files)} files)"
    )
    return True


def handle_test_complete(
    ticket_id: str,
    run_dir: Path,
    repo: str | None,
    worktree_cwd: str | None = None,
) -> None:
    """Orchestrate PR lifecycle for a ticket at TEST_COMPLETE."""
    _log(f"{ticket_id}: TEST_COMPLETE PR lifecycle")
    if not _checkpoint_and_push_before_pr(ticket_id, cwd=worktree_cwd):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(ticket_id, run_dir, repo)
    if not auto_merge_pr(ticket_id, run_dir, repo):
        state_data = _load_state_json(run_dir)
        pr_number = state_data.get("pr_number")
        if pr_number:
            if not detect_pr_conflict(ticket_id, pr_number, run_dir, repo):
                _log(f"{ticket_id}: auto-merge failed but PR #{pr_number} has no conflicts — no state transition needed")
        else:
            _log(f"{ticket_id}: auto-merge failed but no pr_number in state.json — cannot check for conflicts")
        return
    check_and_close_issue(ticket_id, run_dir, repo)
    _sync_runtime_db(ticket_id, run_dir, worktree_cwd=worktree_cwd, repo=repo)


def needs_pr_finalization(run_dir: Path) -> bool:
    """True when TEST_COMPLETE artifacts exist but GitHub issue closure is pending."""
    state = _load_state_json(run_dir)
    if state.get("state") != "TEST_COMPLETE":
        return False
    return not state.get("issue_closed") and not state.get("pr_skipped_no_diff")


__all__ = [
    "auto_merge_pr",
    "check_and_close_issue",
    "configure_log",
    "create_or_update_pr",
    "detect_pr_conflict",
    "handle_test_complete",
    "needs_pr_finalization",
    "_checkpoint_and_push_before_pr",
    "_load_state_json",
    "_pr_body",
    "_save_state_json",
]
