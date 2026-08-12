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

# Branch tickets rebase onto and target when opening/updating PRs.
INTEGRATION_BRANCH = "main"


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


def _resolve_owner_repo(repo: str | None) -> str | None:
    """Return ``owner/name`` for REST calls (avoids GraphQL ``gh pr`` / ``gh issue``)."""
    if repo and "/" in repo.strip():
        return repo.strip()
    try:
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None
    url = (origin.stdout or "").strip()
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def _gh_api(
    path: str,
    *,
    method: str | None = None,
    fields: dict[str, str] | None = None,
    raw_fields: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``gh api`` (REST / core quota). ``fields`` use ``-f``; ``raw_fields`` use ``-F``."""
    cmd = ["gh", "api", path]
    if method:
        cmd += ["--method", method]
    if fields:
        for key, value in fields.items():
            cmd += ["-f", f"{key}={value}"]
    if raw_fields:
        for key, value in raw_fields.items():
            cmd += ["-F", f"{key}={value}"]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def resolve_integration_branch(
    ticket_id: str,
    run_dir: Path,
    repo: str | None = None,
) -> str:
    """Return the branch name tickets integrate into (PR base / rebase target)."""
    _ = (ticket_id, run_dir, repo)  # reserved for per-project overrides later
    return INTEGRATION_BRANCH


def rebase_onto_ref(integration_branch: str) -> str:
    """Git ref to pass to ``git rebase`` for an integration branch."""
    branch = integration_branch.removeprefix("origin/")
    return f"origin/{branch}"


def _list_unmerged_paths(*, cwd: str | Path | None = None) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def rebase_ticket_onto_integration(
    ticket_id: str,
    run_dir: Path,
    *,
    cwd: str | Path | None = None,
    repo: str | None = None,
    push: bool = False,
) -> tuple[bool, list[str]]:
    """Rebase the ticket branch onto the latest integration branch (usually main).

    Batch intake creates branches early; main often moves before planner/coder/
    tester run. Rebasing before those steps avoids stale plans, duplicate
    migrations, and edits against outdated shared files.

    Returns ``(ok, conflicted_files)``. On conflict, leaves the rebase in
    progress so the conflict-resolver can continue, and records
    ``CONFLICT_RESOLUTION_NEEDED`` in ``state.json``.
    """
    work = Path(cwd) if cwd else Path.cwd()
    integration = resolve_integration_branch(ticket_id, run_dir, repo)
    rebase_ref = rebase_onto_ref(integration)

    fetch = subprocess.run(
        ["git", "fetch", "origin", integration],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
    )
    if fetch.returncode != 0:
        err = (fetch.stderr or fetch.stdout or "").strip()
        _log(f"{ticket_id}: integration rebase: git fetch failed: {err}")
        return False, []

    # Already up to date?
    mb = subprocess.run(
        ["git", "merge-base", "HEAD", rebase_ref],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
    )
    tip = subprocess.run(
        ["git", "rev-parse", rebase_ref],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
    )
    if (
        mb.returncode == 0
        and tip.returncode == 0
        and mb.stdout.strip()
        and mb.stdout.strip() == tip.stdout.strip()
    ):
        _log(f"{ticket_id}: integration rebase: already based on {rebase_ref}")
        return True, []

    _log(f"{ticket_id}: integration rebase onto {rebase_ref}")
    rebase = subprocess.run(
        ["git", "rebase", rebase_ref],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
    )
    if rebase.returncode == 0:
        # Optional: renumber migrations if both sides landed without textual conflict
        try:
            from migration_index_fix import fix_duplicate_migration_indexes

            fix = fix_duplicate_migration_indexes(
                work, integration_ref=rebase_ref, cwd=work,
            )
            if fix.changed:
                _log(f"{ticket_id}: integration rebase migration fix: {fix.summary}")
                for src, dst in fix.renames:
                    subprocess.run(
                        ["git", "add", "-A", "--", src, dst],
                        cwd=str(work),
                        capture_output=True,
                        check=False,
                    )
                # Stage journals/snapshots under any migrations/ tree
                for path in work.rglob("migrations"):
                    if path.is_dir() and "node_modules" not in path.parts:
                        subprocess.run(
                            ["git", "add", "-A", "--", str(path)],
                            cwd=str(work),
                            capture_output=True,
                            check=False,
                        )
                subprocess.run(
                    [
                        "git", "commit", "-m",
                        f"chore({ticket_id}): renumber migrations after rebase onto {integration}",
                    ],
                    cwd=str(work),
                    capture_output=True,
                    check=False,
                )
        except Exception as exc:
            _log(f"{ticket_id}: integration rebase migration fix skipped: {exc}")

        if push:
            push_result = subprocess.run(
                ["git", "push", "--force-with-lease", "origin", "HEAD"],
                cwd=str(work),
                capture_output=True,
                text=True,
                check=False,
            )
            if push_result.returncode != 0:
                err = (push_result.stderr or push_result.stdout or "").strip()
                _log(f"{ticket_id}: integration rebase push failed: {err}")
                return False, []
        _log(f"{ticket_id}: integration rebase onto {rebase_ref} ok")
        return True, []

    conflicted = _list_unmerged_paths(cwd=work)

    # Migrations-only conflicts: heal mechanically before handing off to LLM.
    try:
        from migration_index_fix import (
            heal_migrations_only_rebase_conflict,
            migrations_only_conflict_paths,
        )

        if conflicted and migrations_only_conflict_paths(conflicted):
            _log(
                f"{ticket_id}: integration rebase migrations-only conflict "
                f"({len(conflicted)} files) — attempting mechanical heal"
            )
            healed, remaining = heal_migrations_only_rebase_conflict(
                ticket_id=ticket_id,
                conflicted=conflicted,
                integration_ref=rebase_ref,
                cwd=work,
                log=_log,
            )
            if healed:
                if push:
                    push_result = subprocess.run(
                        ["git", "push", "--force-with-lease", "origin", "HEAD"],
                        cwd=str(work),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if push_result.returncode != 0:
                        err = (push_result.stderr or push_result.stdout or "").strip()
                        _log(f"{ticket_id}: integration rebase push failed: {err}")
                        return False, []
                _log(
                    f"{ticket_id}: integration rebase onto {rebase_ref} ok "
                    "(migrations-only conflict healed)"
                )
                return True, []
            conflicted = remaining or conflicted
    except Exception as exc:
        _log(f"{ticket_id}: integration rebase migration heal skipped: {exc}")

    _log(
        f"{ticket_id}: integration rebase onto {rebase_ref} conflicted "
        f"({len(conflicted)} files) — handing off to conflict resolver"
    )
    state = _load_state_json(run_dir)
    pre = state.get("state") or "PLAN_APPROVED"
    state["pre_conflict_state"] = pre
    state["state"] = "CONFLICT_RESOLUTION_NEEDED"
    state["conflict_detected_at"] = _now_iso()
    state["conflicted_files"] = conflicted
    state["updated_at"] = _now_iso()
    state.pop("conflict_clear_reason", None)
    state.pop("conflict_cleared_at", None)
    # Keep rebase in progress — conflict-resolver resumes it.
    _save_state_json(run_dir, state)
    return False, conflicted


def ensure_pr_base_branch(
    ticket_id: str,
    run_dir: Path,
    repo: str | None,
    *,
    base_branch: str | None = None,
) -> bool:
    """Align an existing PR's GitHub base branch with the integration branch."""
    state = _load_state_json(run_dir)
    pr_number = state.get("pr_number")
    if not pr_number:
        return False
    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        _log(f"{ticket_id}: ensure_pr_base: cannot resolve owner/repo")
        return False
    target = base_branch or resolve_integration_branch(ticket_id, run_dir, repo)
    try:
        view = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}")
    except FileNotFoundError:
        _log(f"{ticket_id}: ensure_pr_base: gh not found")
        return False
    if view.returncode != 0:
        err = (view.stderr or view.stdout or "").strip()
        _log(f"{ticket_id}: ensure_pr_base: gh api pr view failed: {err}")
        return False
    try:
        payload = json.loads(view.stdout)
        current_base = ((payload.get("base") or {}).get("ref")) or ""
    except json.JSONDecodeError:
        _log(f"{ticket_id}: ensure_pr_base: invalid JSON from gh api")
        return False
    if current_base == target:
        return True
    try:
        edit = _gh_api(
            f"repos/{owner_repo}/pulls/{pr_number}",
            method="PATCH",
            fields={"base": target},
        )
    except FileNotFoundError:
        return False
    if edit.returncode != 0:
        err = (edit.stderr or edit.stdout or "").strip()
        _log(
            f"{ticket_id}: ensure_pr_base: failed to retarget PR #{pr_number} "
            f"{current_base!r} → {target!r}: {err}"
        )
        return False
    _log(f"{ticket_id}: PR #{pr_number} base retargeted {current_base!r} → {target!r}")
    return True


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
    """Create or update the GitHub PR for a ticket at TEST_COMPLETE. Non-blocking on gh failure.

    Uses REST via ``gh api`` (core quota) — ``gh pr create/list`` hit GraphQL and
    routinely fail when the factory has already burned the GraphQL budget on polls.
    """
    state = _load_state_json(run_dir)
    branch = state.get("branch")
    issue_number = state.get("issue_number")
    pr_number = state.get("pr_number")

    if not branch:
        _log(f"{ticket_id}: create_or_update_pr: no branch in state — skipping")
        return

    if pr_number is not None and state.get("pr_synced"):
        return

    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        _log(f"{ticket_id}: create_or_update_pr: cannot resolve owner/repo — skipping")
        return

    title = _pr_title(ticket_id, run_dir)
    body = _pr_body(ticket_id, issue_number)
    owner = owner_repo.split("/", 1)[0]

    if pr_number is None:
        try:
            list_result = _gh_api(
                f"repos/{owner_repo}/pulls?state=open&head={owner}:{branch}&per_page=5"
            )
            if list_result.returncode == 0 and list_result.stdout.strip():
                existing = json.loads(list_result.stdout)
                if isinstance(existing, list) and existing:
                    pr_number = existing[0]["number"]
                    _log(f"{ticket_id}: found existing PR #{pr_number} — will update")
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            _log(f"{ticket_id}: gh api pr list failed — proceeding with create")

    if pr_number is None:
        prefix = f"ticket/{ticket_id}-"
        try:
            fb_result = _gh_api(f"repos/{owner_repo}/pulls?state=open&per_page=100")
            if fb_result.returncode == 0 and fb_result.stdout.strip():
                all_prs = json.loads(fb_result.stdout)
                matching = [
                    p for p in all_prs
                    if isinstance(p, dict)
                    and str((p.get("head") or {}).get("ref") or "").startswith(prefix)
                ]
                if matching:
                    pr_number = matching[0]["number"]
                    head_ref = (matching[0].get("head") or {}).get("ref", "")
                    _log(
                        f"{ticket_id}: found PR #{pr_number} via branch prefix {prefix!r} "
                        f"(headRef={head_ref!r}) — branch may have been renamed"
                    )
                    state["pr_number"] = pr_number
                    _save_state_json(run_dir, state)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            pass

    if pr_number is not None:
        try:
            result = _gh_api(
                f"repos/{owner_repo}/pulls/{pr_number}",
                method="PATCH",
                fields={"body": body},
            )
            if result.returncode == 0:
                state["pr_synced"] = True
                _save_state_json(run_dir, state)
                _log(f"{ticket_id}: PR #{pr_number} updated")
            else:
                err = (result.stderr or result.stdout or "").strip()
                _log(f"{ticket_id}: gh api pr edit failed (rc={result.returncode}): {err}")
        except FileNotFoundError:
            _log(f"{ticket_id}: gh not found — cannot update PR #{pr_number}")
    else:
        base_branch = resolve_integration_branch(ticket_id, run_dir, repo)
        try:
            result = _gh_api(
                f"repos/{owner_repo}/pulls",
                method="POST",
                fields={
                    "title": title,
                    "head": branch,
                    "base": base_branch,
                    "body": body,
                },
            )
            if result.returncode == 0:
                try:
                    payload = json.loads(result.stdout)
                except json.JSONDecodeError:
                    payload = {}
                pr_number = payload.get("number")
                pr_url = payload.get("html_url") or ""
                if pr_number:
                    state["pr_number"] = int(pr_number)
                    state["pr_synced"] = True
                    _save_state_json(run_dir, state)
                    _log(f"{ticket_id}: PR #{pr_number} created: {pr_url}")
                else:
                    _log(f"{ticket_id}: PR created but number missing in response: {result.stdout[:200]!r}")
            else:
                stderr = (result.stderr or result.stdout or "").strip()
                _log(f"{ticket_id}: gh api pr create failed (rc={result.returncode}): {stderr}")
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

    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        _log(f"{ticket_id}: check_and_close_issue: cannot resolve owner/repo — skipping")
        return

    try:
        result = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}")
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            _log(f"{ticket_id}: gh api pr view failed (rc={result.returncode}): {err}")
            return
        pr_data = json.loads(result.stdout)
    except (json.JSONDecodeError, FileNotFoundError):
        _log(f"{ticket_id}: gh api pr view failed or gh not found")
        return

    # REST: state is open/closed; merged is a boolean (GraphQL used state=MERGED).
    if not pr_data.get("merged"):
        return

    _log(f"{ticket_id}: PR #{pr_number} merged — handling issue closure")

    if not issue_number:
        return

    try:
        close_result = _gh_api(
            f"repos/{owner_repo}/issues/{issue_number}",
            method="PATCH",
            fields={"state": "closed", "state_reason": "completed"},
        )
        if close_result.returncode == 0:
            _log(f"{ticket_id}: issue #{issue_number} closed")
        else:
            err = (close_result.stderr or close_result.stdout or "").strip()
            _log(f"{ticket_id}: gh api issue close failed (rc={close_result.returncode}): {err}")
    except FileNotFoundError:
        _log(f"{ticket_id}: gh not found — cannot close issue #{issue_number}")

    try:
        label_result = _gh_api(
            f"repos/{owner_repo}/issues/{issue_number}/labels/ai-ready",
            method="DELETE",
        )
        if label_result.returncode == 0:
            _log(f"{ticket_id}: removed ai-ready label from issue #{issue_number}")
        elif label_result.returncode != 0:
            err = (label_result.stderr or label_result.stdout or "").strip()
            # 404 = label already gone — fine
            if "Not Found" not in err and "404" not in err:
                _log(f"{ticket_id}: remove ai-ready failed (rc={label_result.returncode}): {err}")
    except FileNotFoundError:
        pass

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


def _fix_migration_indexes_before_pr(
    ticket_id: str,
    run_dir: Path,
    cwd: str | None = None,
) -> bool:
    """Renumber ticket migrations that collide with the integration branch.

    Returns True when files were rewritten (a follow-up checkpoint is needed).
    """
    from migration_index_fix import fix_duplicate_migration_indexes

    work = Path(cwd).resolve() if cwd else Path.cwd()
    integration = resolve_integration_branch(ticket_id, run_dir)
    ref = rebase_onto_ref(integration)
    fetch = subprocess.run(
        ["git", "fetch", "origin", integration],
        cwd=str(work),
        capture_output=True,
        text=True,
        check=False,
    )
    if fetch.returncode != 0:
        _log(
            f"{ticket_id}: pre-PR migration fix: git fetch failed "
            f"(rc={fetch.returncode}) — continuing without renumber"
        )
        return False

    result = fix_duplicate_migration_indexes(work, integration_ref=ref, cwd=work)
    if not result.changed:
        _log(f"{ticket_id}: pre-PR migration fix: {result.summary}")
        return False

    _log(f"{ticket_id}: pre-PR migration fix applied — {result.summary}")
    try:
        checkpoint_transition(
            ticket_id,
            f"chore({ticket_id}): renumber migrations onto {integration}",
            push=True,
            include_code=True,
            cwd=cwd,
        )
        _log(f"{ticket_id}: pre-PR migration fix checkpoint ok")
    except (CheckpointError, DirtyTreeError) as exc:
        _log(f"{ticket_id}: pre-PR migration fix checkpoint failed: {exc}")
        return False
    return True


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

    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        _log(f"{ticket_id}: auto-merge: cannot resolve owner/repo — skipping")
        return False

    try:
        result = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}")
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            _log(f"{ticket_id}: auto-merge: gh api pr view failed (rc={result.returncode}): {err}")
            return False
        pr_data = json.loads(result.stdout)
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False
    except json.JSONDecodeError:
        _log(f"{ticket_id}: auto-merge: invalid JSON from gh api")
        return False

    # REST: state is open/closed; merged is a boolean (GraphQL used state=MERGED).
    if pr_data.get("merged"):
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} already merged — marking state")
        state["pr_merged"] = True
        state["daemon_archived"] = True
        _save_state_json(run_dir, state)
        _sync_runtime_db(ticket_id, run_dir, repo=repo)
        return True
    if (pr_data.get("state") or "").lower() != "open":
        _log(
            f"{ticket_id}: auto-merge: PR #{pr_number} state={pr_data.get('state')!r} "
            "— not open, skipping"
        )
        return False

    mergeable = pr_data.get("mergeable")
    mergeable_state = (pr_data.get("mergeable_state") or "").lower()
    if mergeable is False or mergeable_state == "dirty":
        _log(f"{ticket_id}: auto-merge: PR #{pr_number} has conflicts — skipping")
        return False

    try:
        merge_result = _gh_api(
            f"repos/{owner_repo}/pulls/{pr_number}/merge",
            method="PUT",
            fields={"merge_method": "squash"},
        )
    except FileNotFoundError:
        _log(f"{ticket_id}: auto-merge: gh not found")
        return False

    if merge_result.returncode != 0:
        err = (merge_result.stderr or merge_result.stdout or "").strip()
        _log(f"{ticket_id}: auto-merge: gh api merge failed (rc={merge_result.returncode}): {err}")
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
    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        _log(f"{ticket_id}: conflict detection: cannot resolve owner/repo")
        return False
    try:
        result = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}")
    except FileNotFoundError:
        _log(f"{ticket_id}: conflict detection: gh not found")
        return False
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        _log(f"{ticket_id}: conflict detection: gh api pr view failed (rc={result.returncode}): {err}")
        return False
    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        _log(f"{ticket_id}: conflict detection: invalid JSON from gh api")
        return False

    mergeable = pr_data.get("mergeable")
    mergeable_state = (pr_data.get("mergeable_state") or "").lower()
    if not (mergeable is False or mergeable_state == "dirty"):
        return False

    conflicted_files: list[str] = []
    try:
        files_result = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}/files?per_page=100")
        if files_result.returncode == 0:
            files_data = json.loads(files_result.stdout)
            raw_files = [
                f["filename"] for f in files_data
                if isinstance(f, dict) and "filename" in f
                and not str(f["filename"]).startswith(f"runs/{ticket_id}/")
            ]
            # Drop build/deps noise (backend/target, node_modules, …) so accidental
            # tracked artifacts cannot inflate conflict loops (see timizer T060/T066).
            try:
                from conflict_context_collector import _filter_paths

                conflicted_files = _filter_paths(raw_files, ticket_id)
            except Exception:
                conflicted_files = raw_files
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
    try:
        from conflict_resolution_eligibility import reset_conflict_resolution_auto_retry

        reset_conflict_resolution_auto_retry(run_dir)
    except Exception:
        pass
    _log(
        f"{ticket_id}: PR #{pr_number} is CONFLICTING — transitioned to "
        f"CONFLICT_RESOLUTION_NEEDED (was {pre_conflict_state!r}, {len(conflicted_files)} files)"
    )
    return True


def clear_pr_conflict_if_resolved(
    ticket_id: str,
    pr_number: int,
    run_dir: Path,
    repo: str | None = None,
) -> bool:
    """If the PR is no longer CONFLICTING, clear conflict state and restore pre_conflict_state.

    Returns True when state was cleared (daemon should not keep looping the resolver).
    """
    state = _load_state_json(run_dir)
    if state.get("state") not in ("CONFLICT_RESOLUTION_NEEDED", "CONFLICT_RESOLUTION_FAILED"):
        return False

    owner_repo = _resolve_owner_repo(repo)
    if not owner_repo:
        return False
    try:
        result = _gh_api(f"repos/{owner_repo}/pulls/{pr_number}")
    except FileNotFoundError:
        return False
    if result.returncode != 0:
        return False
    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False

    mergeable = pr_data.get("mergeable")
    mergeable_state = (pr_data.get("mergeable_state") or "").lower()
    if mergeable is False or mergeable_state == "dirty":
        return False
    if mergeable is None and mergeable_state in ("unknown", ""):
        # Still computing — leave conflict state alone.
        return False

    restored = state.get("pre_conflict_state") or "TEST_COMPLETE"
    if restored in ("CONFLICT_RESOLUTION_NEEDED", "CONFLICT_RESOLUTION_FAILED", "CONFLICT_RESOLVING"):
        restored = "TEST_COMPLETE"
    state["state"] = restored
    state.pop("conflicted_files", None)
    state.pop("conflict_detected_at", None)
    state.pop("conflict_pr_number", None)
    state["updated_at"] = _now_iso()
    state["conflict_cleared_at"] = _now_iso()
    state["conflict_clear_reason"] = (
        f"PR #{pr_number} mergeable={mergeable!r} mergeable_state={mergeable_state!r}"
    )
    _save_state_json(run_dir, state)
    _log(
        f"{ticket_id}: PR #{pr_number} is mergeable={mergeable!r}/{mergeable_state!r} "
        f"— cleared conflict loop, restored state={restored!r}"
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
    _fix_migration_indexes_before_pr(ticket_id, run_dir, cwd=worktree_cwd)
    if not _checkpoint_and_push_before_pr(ticket_id, cwd=worktree_cwd):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    ensure_pr_base_branch(ticket_id, run_dir, repo)
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
    "INTEGRATION_BRANCH",
    "auto_merge_pr",
    "check_and_close_issue",
    "configure_log",
    "create_or_update_pr",
    "clear_pr_conflict_if_resolved",
    "detect_pr_conflict",
    "ensure_pr_base_branch",
    "handle_test_complete",
    "needs_pr_finalization",
    "rebase_onto_ref",
    "rebase_ticket_onto_integration",
    "resolve_integration_branch",
    "_checkpoint_and_push_before_pr",
    "_fix_migration_indexes_before_pr",
    "_load_state_json",
    "_pr_body",
    "_save_state_json",
]
