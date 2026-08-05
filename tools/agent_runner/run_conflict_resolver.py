#!/usr/bin/env python3
"""Conflict resolver executor for ai-dev-factory.

Runs inside the ticket worktree:
1. Fetches origin and rebases onto the integration branch (``main`` by default).
2. On rebase conflict: collects context, invokes AI agent to edit files.
3. Loops until all conflicts cleared or MAX_RESOLVER_PASSES reached.
4. Stages only conflicted files per pass.
5. Runs tests.
6. Commits artifacts with message conflict(T{id}): resolve conflicts against <base>.
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

_CONFLICT_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})

ROOT = Path(__file__).resolve().parent
_RUN_STEP_PATH = ROOT / "run_step.py"
_CONTEXT_COLLECTOR_PATH = ROOT / "conflict_context_collector.py"

_tpl_spec = importlib.util.spec_from_file_location(
    "_ticket_pr_lifecycle_cr", ROOT / "ticket_pr_lifecycle.py",
)
_tpl_mod = importlib.util.module_from_spec(_tpl_spec)  # type: ignore[arg-type]
_tpl_spec.loader.exec_module(_tpl_mod)  # type: ignore[union-attr]
resolve_integration_branch = _tpl_mod.resolve_integration_branch
rebase_onto_ref = _tpl_mod.rebase_onto_ref
ensure_pr_base_branch = _tpl_mod.ensure_pr_base_branch
del _tpl_spec, _tpl_mod

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

_rc_spec = importlib.util.spec_from_file_location("_runtime_checkpoint", ROOT / "runtime_checkpoint.py")
_rc_mod = importlib.util.module_from_spec(_rc_spec)  # type: ignore[arg-type]
_rc_spec.loader.exec_module(_rc_mod)  # type: ignore[union-attr]
is_ignorable_runtime_dirty_path = _rc_mod.is_ignorable_runtime_dirty_path
parse_porcelain_paths = _rc_mod.parse_porcelain_paths
del _rc_spec, _rc_mod


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


def _write_state(run_dir: Path, data: dict) -> None:
    data["updated_at"] = _now_iso()
    state_file = run_dir / "state.json"
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(state_file)


def _transition_state(
    ticket_id: str,
    run_dir: Path,
    new_state: str,
    *,
    backup: dict | None = None,
    conflicted_files: list[str] | None = None,
) -> None:
    """Transition workflow state, restoring conflict metadata when ``backup`` is set.

    During rebase, tracked ``runs/{ticket}/state.json`` can rewind to an older
    commit — pass the resolver's in-memory snapshot so ``pre_conflict_state`` survives.
    """
    if backup is not None:
        files = conflicted_files
        if files is None:
            raw = backup.get("conflicted_files")
            files = list(raw) if isinstance(raw, list) else []
        _persist_conflict_state(run_dir, backup, new_state, files)
        _log(ticket_id, f"state → {new_state}")
        return
    state_file = run_dir / "state.json"
    data = json.loads(state_file.read_text(encoding="utf-8"))
    data["state"] = new_state
    _write_state(run_dir, data)
    _log(ticket_id, f"state → {new_state}")


def _persist_conflict_state(
    run_dir: Path,
    backup: dict,
    new_state: str,
    conflicted_files: list[str],
) -> None:
    """Restore conflict metadata after rebase rewinds tracked ``state.json``."""
    ticket_id = backup.get("ticket_id") or run_dir.name
    prefix = _runtime_path_prefix(ticket_id)
    source_files = [f for f in conflicted_files if not f.startswith(prefix)]
    data = dict(backup)
    pre = data.get("pre_conflict_state") or backup.get("state", "")
    if pre in _CONFLICT_STATES:
        pre = backup.get("pre_conflict_state") or "IMPLEMENTATION_REVIEW_NEEDED"
    data["pre_conflict_state"] = pre
    data["state"] = new_state
    data["conflicted_files"] = source_files
    if not data.get("conflict_detected_at"):
        data["conflict_detected_at"] = _now_iso()
    _write_state(run_dir, data)


def _ensure_conflict_dir(run_dir: Path) -> Path:
    """``git clean`` may remove ``runs/{ticket}/conflict/`` mid-run — recreate it."""
    conflict_dir = run_dir / "conflict"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    return conflict_dir


def _write_error_log(run_dir: Path, message: str, stderr: str = "") -> None:
    conflict_dir = _ensure_conflict_dir(run_dir)
    error_path = conflict_dir / "error.log"
    content = f"[{_now_iso()}] {message}\n"
    if stderr.strip():
        content += f"\n--- stderr ---\n{stderr.strip()}\n"
    with error_path.open("a", encoding="utf-8") as fh:
        fh.write(content)


def _normalize_branch(name: str) -> str:
    if name.startswith("refs/heads/"):
        return name[len("refs/heads/"):]
    return name


def _rebase_head_branch() -> str | None:
    result = _run_git(["rev-parse", "--git-path", "rebase-merge/head-name"])
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    return _normalize_branch(raw) if raw else None


def _get_current_branch() -> str:
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("failed to determine current git branch")
    branch = _normalize_branch(result.stdout.strip())
    if branch == "HEAD":
        rebase_branch = _rebase_head_branch()
        if rebase_branch:
            return rebase_branch
    return branch


def _list_conflicted_files() -> list[str]:
    result = _run_git(["diff", "--name-only", "--diff-filter=U"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _runtime_path_prefix(ticket_id: str) -> str:
    return f"runs/{ticket_id}/"


def _is_runtime_artifact_path(path: str, ticket_id: str | None = None) -> bool:
    """True for workflow ``runs/``, deps, and build trees — never AI-merge these.

    Other tickets' ``runs/TXXX/`` often land on ``main`` via merged PRs. When this
    ticket rebases, those paths conflict, but they are not this ticket's source
    code and must not be handed to the conflict-resolver agent. Same for
    ``node_modules`` and Maven/Gradle ``target/`` / ``build/`` output that
    sometimes gets committed by accident.
    """
    _ = ticket_id
    if not path:
        return False
    if path.startswith("./"):
        path = path[2:]
    if path == "runs" or path.startswith("runs/"):
        return True
    if path == "node_modules" or path.startswith("node_modules/"):
        return True
    if "/node_modules/" in path or path.endswith("/node_modules"):
        return True
    # Build / dependency / bytecode output — never resolve via the agent.
    parts = path.split("/")
    if "target" in parts or "build" in parts or "dist" in parts:
        return True
    if "__pycache__" in parts or path.endswith((".pyc", ".class")):
        return True
    if path == ".venv" or path.startswith(".venv/") or "/.venv/" in path:
        return True
    return False


def _split_conflicts(ticket_id: str, files: list[str]) -> tuple[list[str], list[str]]:
    source = [f for f in files if not _is_runtime_artifact_path(f, ticket_id)]
    runtime = [f for f in files if _is_runtime_artifact_path(f, ticket_id)]
    return source, runtime


def _has_conflict_markers(path: str) -> bool:
    """Return True only for a real conflict marker *block*.

    A bare substring check is too naive: ``run_conflict_resolver.py`` and
    ``tests/test_conflict_resolver.py`` contain the literal ``<<<<<<< `` in
    source/fixtures, which previously made every resolver pass fail forever.
    """
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    has_start = False
    has_mid = False
    for line in text.splitlines():
        if line.startswith("<<<<<<< "):
            has_start = True
            has_mid = False
        elif has_start and line.strip() == "=======":
            has_mid = True
        elif has_start and has_mid and line.startswith(">>>>>>> "):
            return True
    return False


def _scan_source_marker_conflicts(ticket_id: str) -> list[str]:
    """Return *unmerged* source paths that still contain conflict marker blocks.

    Intentionally does **not** rglob the whole tree: that falsely flagged
    files that merely mention conflict markers in code or tests.
    """
    found: list[str] = []
    for rel in _list_conflicted_files():
        if _is_runtime_artifact_path(rel, ticket_id):
            continue
        if _has_conflict_markers(rel):
            found.append(rel)
    return sorted(found)


def _effective_source_conflicts(ticket_id: str) -> list[str]:
    """Merge git unmerged paths with on-disk marker scan (source files only)."""
    unmerged = _list_conflicted_files()
    source, runtime = _split_conflicts(ticket_id, unmerged)
    marker_paths = _scan_source_marker_conflicts(ticket_id)
    merged: list[str] = []
    seen: set[str] = set()
    for path in source + marker_paths:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return merged


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
    if result.returncode == 5:
        return (
            f"# Test Report — conflict resolution for {ticket_id}\n"
            f"Generated at: {_now_iso()}\n"
            "Exit code: 0\n\n"
            "No pytest tests collected — skipped.\n"
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


def _blocking_dirty_paths(porcelain: str, ticket_id: str) -> list[str]:
    """Return dirty paths that should block rebase (real source edits only)."""
    blocking: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().split(" -> ")[-1]
        if _is_runtime_artifact_path(path, ticket_id):
            continue
        if is_ignorable_runtime_dirty_path(path):
            continue
        blocking.append(path)
    return blocking


def _runtime_tree_porcelain(ticket_id: str) -> str:
    prefix = _runtime_path_prefix(ticket_id)
    result = _run_git(["status", "--porcelain", "--", prefix])
    if result.returncode != 0:
        return "<git status failed>"
    return result.stdout


def _scrub_ticket_runtime_dir(ticket_id: str) -> None:
    """Reset tracked runtime artifacts and drop *all* untracked files under
    ``runs/{ticket}/`` so they cannot block ``git rebase`` / ``--continue``.

    Live workflow state is held in-memory (``state_backup``) and rewritten after
    each transition — leaving an untracked ``state.json`` on disk will make
    later commits that recreate ``runs/{ticket}/`` fail with "would be
    overwritten by merge".
    """
    import shutil

    prefix = _runtime_path_prefix(ticket_id)
    _run_git(["checkout", "HEAD", "--", prefix])
    # Wipe untracked scratch under this ticket's runs tree entirely.
    _run_git(["clean", "-fd", "--", prefix.rstrip("/")])
    untracked = _run_git(["ls-files", "--others", "--exclude-standard", prefix])
    if untracked.returncode == 0:
        for rel in untracked.stdout.splitlines():
            rel = rel.strip()
            if not rel:
                continue
            path = Path(rel)
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    _run_git(["checkout", "HEAD", "--", prefix])


def _try_resume_clean_rebase(ticket_id: str, run_dir: Path) -> bool:
    """If rebase is stuck with no unmerged paths, scrub noise and continue.

    Returns True when the rebase finished or advanced to real conflicts.
    """
    if not _rebase_in_progress():
        return False
    if _list_conflicted_files():
        return False
    _log(ticket_id, "rebase stuck with no unmerged files — scrubbing and continuing")
    _scrub_ticket_runtime_dir(ticket_id)
    cont = _run_rebase_continue(ticket_id)
    if cont.returncode == 0:
        return True
    out_lower = (cont.stdout + cont.stderr).lower()
    if "nothing to commit" in out_lower or "no changes" in out_lower:
        _run_git(["rebase", "--skip"])
        return True
    if _list_conflicted_files():
        return True
    detail = "\n".join(
        x for x in (cont.stdout.strip(), cont.stderr.strip()) if x
    ) or "<no output>"
    _write_error_log(run_dir, f"stuck rebase --continue failed: {detail}")
    return False


def _blocking_runtime_dirty(porcelain: str) -> list[str]:
    """Return non-ignorable dirty paths under ``runs/{ticket}/``."""
    return [
        path
        for path in parse_porcelain_paths(porcelain)
        if not is_ignorable_runtime_dirty_path(path)
    ]


def _rebase_in_progress() -> bool:
    for subpath in ("rebase-merge", "rebase-apply"):
        result = _run_git(["rev-parse", "--git-path", subpath])
        if result.returncode != 0:
            continue
        if Path(result.stdout.strip()).exists():
            return True
    return False


def _prepare_clean_tree_for_rebase(ticket_id: str) -> bool:
    """Ensure the worktree is clean enough for ``git rebase``.

    The in-memory ``state.json`` backup lives outside git — reset the tracked
    ``runs/{ticket}/`` tree so ``runtime.log``, deleted locks, and workflow
    state edits do not block the rebase.
    """
    _scrub_ticket_runtime_dir(ticket_id)

    runtime_dirty = _runtime_tree_porcelain(ticket_id).strip()
    blocking_runtime = _blocking_runtime_dirty(runtime_dirty) if runtime_dirty else []
    if blocking_runtime:
        _log(
            ticket_id,
            f"runtime tree still dirty after scrub: {', '.join(blocking_runtime)}",
        )
        return False

    remaining = _run_git(["status", "--porcelain"])
    if remaining.returncode != 0:
        return False
    blocking = _blocking_dirty_paths(remaining.stdout, ticket_id)
    if blocking:
        _log(ticket_id, f"blocking dirty paths before rebase: {blocking}")
        return False
    return True


def _auto_resolve_runtime_conflicts(ticket_id: str, paths: list[str]) -> None:
    """Auto-stage runtime/artifact conflicts without invoking the AI agent.

    During rebase, ``--theirs`` is the commit being replayed (ticket branch) and
    ``--ours`` is upstream. Keep this ticket's own ``runs/{ticket}/`` from the
    ticket branch; for every other runtime/build noise path (foreign ``runs/``,
    ``node_modules``, ``target/``, …), take upstream so the agent never merges them.
    """
    own_prefix = _runtime_path_prefix(ticket_id)
    for path in paths:
        keep_ticket = path.startswith(own_prefix)
        # Rebase inverts merge semantics: --theirs = replayed commit.
        preferred = "--theirs" if keep_ticket else "--ours"
        fallback = "--ours" if keep_ticket else "--theirs"
        result = _run_git(["checkout", preferred, "--", path])
        if result.returncode != 0:
            _run_git(["checkout", fallback, "--", path])
        _run_git(["add", "--", path])


# GitHub rejects blobs over 100 MB; keep a safer ceiling for runtime artifacts.
_MAX_COMMIT_ARTIFACT_BYTES = 5 * 1024 * 1024


def _purge_oversized_runtime_artifacts(ticket_id: str) -> None:
    """Delete oversized conflict dumps so they cannot be committed/pushed."""
    root = Path("runs") / ticket_id
    for path in list(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size <= _MAX_COMMIT_ARTIFACT_BYTES:
            continue
        rel = path.as_posix()
        _log(ticket_id, f"purging oversized runtime artifact ({size} bytes): {rel}")
        path.unlink(missing_ok=True)
        _run_git(["rm", "-f", "--ignore-unmatch", "--", rel])


def _unstage_noise_paths(ticket_id: str) -> None:
    """Keep foreign ``runs/`` and node_modules out of the resolution commit."""
    staged = _run_git(["diff", "--cached", "--name-only"])
    if staged.returncode != 0:
        return
    own_prefix = _runtime_path_prefix(ticket_id)
    drop: list[str] = []
    for path in staged.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if _is_runtime_artifact_path(path, ticket_id) and not path.startswith(own_prefix):
            drop.append(path)
            continue
        if path.startswith(own_prefix):
            try:
                if Path(path).is_file() and Path(path).stat().st_size > _MAX_COMMIT_ARTIFACT_BYTES:
                    drop.append(path)
            except OSError:
                pass
    if drop:
        _log(ticket_id, f"unstaging noise paths from resolution commit: {drop[:20]}")
        _run_git(["reset", "HEAD", "--", *drop])


def _scrub_before_rebase_continue(ticket_id: str) -> None:
    """Drop unstaged runtime noise so ``git rebase --continue`` is not blocked."""
    _scrub_ticket_runtime_dir(ticket_id)


def _run_rebase_continue(ticket_id: str) -> subprocess.CompletedProcess[str]:
    _scrub_before_rebase_continue(ticket_id)
    env = dict(os.environ)
    env["GIT_EDITOR"] = "true"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        ["git", "rebase", "--continue"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _advance_past_runtime_conflicts(
    ticket_id: str,
    run_dir: Path,
    data: dict,
    *,
    max_steps: int = 128,
) -> list[str] | None:
    """Auto-resolve runtime/build conflicts and continue until source conflicts.

    Each ``git rebase --continue`` can surface a new wave of foreign ``runs/``,
    ``node_modules``, or ``target/`` conflicts on later commits. Those must be
    auto-resolved in-loop — never treated as a hard failure.
    """
    for step in range(max_steps):
        raw = _list_conflicted_files()
        source = _effective_source_conflicts(ticket_id)
        _, runtime = _split_conflicts(ticket_id, raw)

        if runtime:
            _log(ticket_id, f"auto-resolving runtime path conflicts: {runtime}")
            _auto_resolve_runtime_conflicts(ticket_id, runtime)

        if source:
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", source)
            return source

        if not _rebase_in_progress():
            return []

        if raw:
            # Runtime-only unmerged paths were resolved; re-check before continue.
            continue

        cont = _run_rebase_continue(ticket_id)
        if cont.returncode == 0:
            continue

        out_lower = (cont.stdout + cont.stderr).lower()
        if "nothing to commit" in out_lower or "no changes" in out_lower:
            _run_git(["rebase", "--skip"])
            continue

        # Untracked runs/{ticket}/ (e.g. live state.json) blocks applying a
        # commit that recreates those paths — scrub and retry once.
        if "untracked working tree files would be overwritten" in out_lower:
            _log(ticket_id, "rebase --continue blocked by untracked runtime files; scrubbing")
            _scrub_ticket_runtime_dir(ticket_id)
            cont = _run_rebase_continue(ticket_id)
            if cont.returncode == 0:
                continue
            out_lower = (cont.stdout + cont.stderr).lower()
            if "nothing to commit" in out_lower or "no changes" in out_lower:
                _run_git(["rebase", "--skip"])
                continue

        source = _effective_source_conflicts(ticket_id)
        if source:
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", source)
            return source

        # Continue failed because the next commit only conflicts on runtime/build
        # noise — loop so the next iteration auto-resolves and continues.
        raw_after = _list_conflicted_files()
        _, runtime_after = _split_conflicts(ticket_id, raw_after)
        if runtime_after:
            _log(
                ticket_id,
                f"rebase --continue hit runtime-only conflicts; continuing auto-resolve "
                f"({len(runtime_after)} paths)",
            )
            continue

        if raw_after:
            # Unmerged paths that somehow aren't classified — still try once more
            # after re-split rather than aborting immediately.
            _log(ticket_id, f"rebase --continue left unclassified conflicts: {raw_after}")
            continue

        detail = "\n".join(
            x for x in (cont.stdout.strip(), cont.stderr.strip()) if x
        ) or "<no output>"
        _write_error_log(run_dir, f"rebase --continue failed (runtime step {step + 1}): {detail}")
        return None

    _write_error_log(run_dir, f"exceeded {max_steps} runtime conflict advance steps")
    return None


def _scrub_runtime_noise_before_rebase(ticket_id: str) -> None:
    """Drop volatile runtime paths immediately before ``git rebase``."""
    _scrub_ticket_runtime_dir(ticket_id)


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
    state_backup = dict(data)
    _log(ticket_id, f"start branch={branch}")

    # Safety guard: never run on main
    try:
        current_branch = _get_current_branch()
    except RuntimeError as exc:
        _log(ticket_id, f"failed to read branch: {exc}")
        _write_error_log(run_dir, str(exc))
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    if current_branch == "main":
        msg = "safety: refusing to resolve conflicts on 'main' branch"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # Verify branch matches state
    if branch and _normalize_branch(current_branch) != _normalize_branch(branch):
        msg = f"branch mismatch: current={current_branch!r} state={branch!r}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    conflict_dir = _ensure_conflict_dir(run_dir)

    # 1. fetch origin
    _log(ticket_id, "git fetch origin")
    fetch = _run_git(["fetch", "origin"])
    if fetch.returncode != 0:
        msg = f"git fetch failed: {fetch.stderr.strip()}"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg, fetch.stderr)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # 2. git rebase onto the integration branch (or resume an in-progress rebase)
    integration_branch = resolve_integration_branch(ticket_id, run_dir)
    rebase_ref = rebase_onto_ref(integration_branch)
    rebase_had_conflicts = False
    if _rebase_in_progress():
        conflicted_files = _list_conflicted_files()
        if conflicted_files:
            _log(ticket_id, f"resuming in-progress rebase conflicts: {conflicted_files}")
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
            rebase_had_conflicts = True
        elif _try_resume_clean_rebase(ticket_id, run_dir):
            _log(ticket_id, "resumed stuck rebase after scrub")
            # Fall through: either done or new conflicts — re-check below via
            # _advance_past_runtime_conflicts / conflicted_files listing.
            conflicted_files = _list_conflicted_files()
            if conflicted_files:
                _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
                rebase_had_conflicts = True
            elif _rebase_in_progress():
                # Still rebasing — let the advance loop finish it.
                rebase_had_conflicts = True
            else:
                rebase_had_conflicts = False
        else:
            msg = "rebase in progress but no unmerged files found"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2
    else:
        if not _prepare_clean_tree_for_rebase(ticket_id):
            remaining = _run_git(["status", "--porcelain"])
            if remaining.returncode != 0:
                blocking = ["<git status failed>"]
            else:
                blocking = _blocking_dirty_paths(remaining.stdout, ticket_id)
                if not blocking:
                    # Own-ticket runtime dirt that survived scrub (reported separately).
                    blocking = _blocking_runtime_dirty(
                        _runtime_tree_porcelain(ticket_id),
                    ) or ["<unknown dirty tree after scrub>"]
            msg = (
                "failed to prepare clean tree before rebase"
                f" — blocking paths: {blocking}"
            )
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2

        _scrub_runtime_noise_before_rebase(ticket_id)
        rebase = _run_git(["rebase", rebase_ref])
        _log(ticket_id, f"git rebase {rebase_ref} exit={rebase.returncode}")

        if rebase.returncode != 0:
            conflicted_files = _list_conflicted_files()
            if not conflicted_files:
                msg = f"rebase failed with no conflict markers: {rebase.stderr.strip()}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, rebase.stderr)
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            _log(ticket_id, f"conflicts detected: {conflicted_files}")
            _persist_conflict_state(run_dir, data, "CONFLICT_RESOLVING", conflicted_files)
            rebase_had_conflicts = True

    if rebase_had_conflicts:
        conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
        if conflicted_files is None:
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2
        if not conflicted_files:
            rebase_had_conflicts = False

    if rebase_had_conflicts:
        prompt_path = Path("prompts") / "generic" / "conflict-resolver.md"
        if not prompt_path.exists():
            msg = f"prompt not found: {prompt_path}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg)
            _abort_rebase(ticket_id)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
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
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
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
                detail = (stdout or stderr_ai or "").strip()
                msg = f"AI resolver failed (rc={rc}) pass {pass_count}"
                if detail:
                    msg = f"{msg}: {detail[:800]}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, stderr_ai)
                (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            (conflict_dir / "resolution.md").write_text(stdout or "", encoding="utf-8")

            # Check which files still have markers after AI edit (before staging)
            still_unresolved_markers = [f for f in pass_conflicted if _has_conflict_markers(f)]
            if still_unresolved_markers:
                msg = (
                    f"AI resolver pass {pass_count} finished but conflict markers remain in:"
                    f" {still_unresolved_markers}"
                )
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, stderr_ai)
                conflicted_files = still_unresolved_markers
                continue

            # Stage only the conflicted files (not git add -A)
            staged = list(pass_conflicted)
            add = _run_git(["add", "--"] + staged)
            if add.returncode != 0:
                msg = f"git add failed: {add.stderr.strip()}"
                _log(ticket_id, msg)
                _write_error_log(run_dir, msg, add.stderr)
                _abort_rebase(ticket_id)
                _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                return 2

            # git rebase --continue
            continue_result = _run_rebase_continue(ticket_id)
            continue_rc = continue_result.returncode

            if continue_rc != 0:
                out_lower = (continue_result.stdout + continue_result.stderr).lower()
                if "nothing to commit" in out_lower or "no changes" in out_lower:
                    _run_git(["rebase", "--skip"])
                    _log(ticket_id, "rebase --skip (nothing to commit)")
                    conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                    if conflicted_files is None:
                        _abort_rebase(ticket_id)
                        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                        return 2
                    continue
                else:
                    new_conflicted = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                    if new_conflicted is None:
                        _abort_rebase(ticket_id)
                        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                        return 2
                    # [] means runtime-only conflicts were cleared and the rebase
                    # finished (or has no further source conflicts). Do NOT treat
                    # that as a hard failure — the previous continue_rc!=0 was
                    # expected when the next commit only conflicted on noise.
                    _log(ticket_id, (
                        f"[pass {pass_count}/{MAX_RESOLVER_PASSES}]"
                        f" conflicted={pass_conflicted}"
                        f" | staged={staged}"
                        f" | unresolved={still_unresolved_markers}"
                        f" | continue_rc={continue_rc}"
                        f" | next_source={new_conflicted}"
                    ))
                    conflicted_files = new_conflicted
                    continue
            else:
                # Successful continue — check for conflicts from the next commit
                conflicted_files = _advance_past_runtime_conflicts(ticket_id, run_dir, data)
                if conflicted_files is None:
                    _abort_rebase(ticket_id)
                    _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
                    return 2

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
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
            return 2

        _log(ticket_id, f"all conflicts resolved after {pass_count} pass(es)")

    else:
        # Clean rebase — write resolution.md noting no conflicts needed
        conflict_dir = _ensure_conflict_dir(run_dir)
        res_path = conflict_dir / "resolution.md"
        if not res_path.exists():
            res_path.write_text(
                f"# Resolution — {ticket_id}\n\n"
                f"Rebase onto {rebase_ref} completed with no conflicts.\n"
                f"Generated at: {_now_iso()}\n",
                encoding="utf-8",
            )
        _log(ticket_id, "rebase clean — no conflicts")

    # 3. run tests
    conflict_dir = _ensure_conflict_dir(run_dir)
    _log(ticket_id, "running tests")
    test_report = _run_tests(ticket_id, run_dir)
    test_report_path = conflict_dir / "test-report.md"
    test_report_path.write_text(test_report, encoding="utf-8")
    _log(ticket_id, f"test-report written: {test_report_path}")

    if "Exit code: 0" not in test_report and "skipped" not in test_report.lower():
        msg = "tests failed after conflict resolution"
        _log(ticket_id, msg)
        _write_error_log(run_dir, msg)
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    # 4. commit resolution artifacts — never push runtime noise or oversized blobs
    _log(ticket_id, "staging and committing resolution artifacts")
    _purge_oversized_runtime_artifacts(ticket_id)
    add_all = _run_git(["add", "-A"])
    if add_all.returncode != 0:
        _log(ticket_id, f"git add before commit failed: {add_all.stderr.strip()}")
    _unstage_noise_paths(ticket_id)

    commit_msg = f"conflict({ticket_id}): resolve conflicts against {integration_branch}"
    commit = _run_git(["commit", "-m", commit_msg])
    if commit.returncode != 0:
        out = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in out:
            _log(ticket_id, "nothing to commit after resolution")
        else:
            msg = f"commit failed: {commit.stderr.strip()}"
            _log(ticket_id, msg)
            _write_error_log(run_dir, msg, commit.stderr)
            _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
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
        _transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED", backup=state_backup)
        return 2

    _log(ticket_id, "push succeeded")
    ensure_pr_base_branch(ticket_id, run_dir, None)

    # 6. transition after clean rebase + passing tests
    _transition_state(
        ticket_id, run_dir, "CONFLICT_RESOLVED_REVIEW_NEEDED", backup=state_backup,
    )
    try:
        from conflict_resolution_eligibility import reset_conflict_resolution_auto_retry

        reset_conflict_resolution_auto_retry(run_dir)
    except Exception as exc:
        _log(ticket_id, f"clear conflict retry state: skipped — {exc}")
    try:
        state_after = json.loads(state_file.read_text(encoding="utf-8"))
        rt_path = ROOT / "run_ticket.py"
        spec = importlib.util.spec_from_file_location("_run_ticket_finalize", rt_path)
        rt_mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(rt_mod)  # type: ignore[union-attr]
        final_state = rt_mod._maybe_auto_finalize_conflict_resolution(
            ticket_id, state_after,
        )
    except Exception as exc:
        _log(ticket_id, f"auto-finalize-conflict: skipped — {exc}")
        final_state = None

    if final_state:
        _log(ticket_id, f"done → {final_state} (auto-finalize)")
    else:
        _log(ticket_id, "done → CONFLICT_RESOLVED_REVIEW_NEEDED")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conflict resolver executor")
    parser.add_argument("ticket_id")
    parser.add_argument("--exec-cmd", required=True, help="AI runtime command")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    run_dir = Path("runs") / args.ticket_id
    try:
        return resolve_conflicts(args.ticket_id, args.exec_cmd)
    except Exception as exc:
        if run_dir.joinpath("state.json").is_file():
            _write_error_log(run_dir, f"uncaught resolver error: {exc}")
            try:
                _transition_state(args.ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")
            except Exception:
                pass
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
