#!/usr/bin/env python3
"""Mechanically renumber colliding Drizzle/ORM migration indexes.

When ``main`` and a ticket branch both add ``NNNN_*.sql``, keep main's file and
rename the ticket migration(s) to ``max+1``, ``max+2``, … updating journal +
snapshots together. No LLM required.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("migration_index_fix")

MIGRATION_SQL_NAME = re.compile(r"^(\d{4})_(.+)\.sql$")
_SKIP_PARTS = frozenset({"node_modules", ".git", "dist", "build", "target", ".venv"})


@dataclass
class MigrationFixResult:
    """Outcome of a mechanical migration-index fix pass."""

    changed: bool = False
    renames: list[tuple[str, str]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.changed:
            return "no migration index collisions"
        lines = [f"renamed {len(self.renames)} migration(s):"]
        for src, dst in self.renames:
            lines.append(f"  {src} → {dst}")
        return "\n".join(lines)


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def list_migration_sql_files(root: Path) -> list[Path]:
    """Return sorted migration SQL paths under ``root`` (relative discovery)."""
    found: list[Path] = []
    for path in root.rglob("*.sql"):
        if "migrations" not in path.parts:
            continue
        if any(part in _SKIP_PARTS for part in path.parts):
            continue
        if not MIGRATION_SQL_NAME.match(path.name):
            continue
        found.append(path)
    return sorted(found)


def duplicate_migration_path_groups(root: Path) -> list[list[Path]]:
    """Groups of absolute Paths that share the same numeric migration index."""
    by_dir_index: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for path in list_migration_sql_files(root):
        match = MIGRATION_SQL_NAME.match(path.name)
        if not match:
            continue
        by_dir_index[(path.parent, match.group(1))].append(path)
    return [files for files in by_dir_index.values() if len(files) >= 2]


def find_duplicate_migration_indexes(root: Path) -> list[str]:
    """Human-readable duplicate-index errors (empty when OK)."""
    errors: list[str] = []
    for files in duplicate_migration_path_groups(root):
        match = MIGRATION_SQL_NAME.match(files[0].name)
        idx = match.group(1) if match else "?"
        listed = ", ".join(sorted(p.as_posix() for p in files))
        errors.append(
            f"duplicate migration index {idx}: {listed} "
            f"— renumber the ticket migration to the next free index"
        )
    return errors


def _migration_dirs(root: Path) -> list[Path]:
    dirs: set[Path] = set()
    for path in list_migration_sql_files(root):
        dirs.add(path.parent)
    return sorted(dirs)


def _parse_index_suffix(name: str) -> tuple[int, str] | None:
    match = MIGRATION_SQL_NAME.match(name)
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def _files_on_ref(ref: str, migrations_dir: Path, *, cwd: Path) -> set[str]:
    """Basenames of ``*.sql`` under ``migrations_dir`` that exist on ``ref``."""
    try:
        rel = migrations_dir.relative_to(cwd).as_posix()
    except ValueError:
        rel = migrations_dir.as_posix()
    result = _run_git(["ls-tree", "-r", "--name-only", ref, "--", rel], cwd=cwd)
    if result.returncode != 0:
        return set()
    names: set[str] = set()
    for line in result.stdout.splitlines():
        path = line.strip()
        if not path.endswith(".sql"):
            continue
        names.add(Path(path).name)
    return names


def _next_free_index(used: set[int]) -> int:
    """Next migration index after the highest already used (no filling 0000 gaps)."""
    if not used:
        return 0
    return max(used) + 1


def _load_journal(meta_dir: Path) -> dict:
    journal_path = meta_dir / "_journal.json"
    if not journal_path.is_file():
        return {"version": "7", "dialect": "postgresql", "entries": []}
    try:
        data = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": "7", "dialect": "postgresql", "entries": []}
    if not isinstance(data, dict):
        return {"version": "7", "dialect": "postgresql", "entries": []}
    data.setdefault("entries", [])
    return data


def _save_journal(meta_dir: Path, journal: dict) -> None:
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / "_journal.json"
    path.write_text(json.dumps(journal, indent=4) + "\n", encoding="utf-8")


def _copy_snapshot_for_new_index(meta_dir: Path, old_index: int, new_index: int) -> bool:
    """Copy ``NNNN_snapshot.json`` to the new index when missing (keep main's file)."""
    import shutil

    old_path = meta_dir / f"{old_index:04d}_snapshot.json"
    new_path = meta_dir / f"{new_index:04d}_snapshot.json"
    if new_path.is_file() or not old_path.is_file():
        return False
    shutil.copy2(old_path, new_path)
    return True


def _relink_snapshot_prev_ids(meta_dir: Path) -> None:
    """Chain each snapshot's ``prevId`` to the previous index's ``id`` when possible."""
    snapshots: list[tuple[int, Path, dict]] = []
    for path in sorted(meta_dir.glob("*_snapshot.json")):
        stem = path.name.replace("_snapshot.json", "")
        if not stem.isdigit():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "id" not in data:
            continue
        snapshots.append((int(stem), path, data))
    snapshots.sort(key=lambda item: item[0])
    prev_id: str | None = None
    for _idx, path, data in snapshots:
        if prev_id is not None and data.get("prevId") != prev_id:
            data["prevId"] = prev_id
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        prev_id = str(data.get("id") or prev_id)


def _indexes_on_ref(ref: str, migrations_dir: Path, *, cwd: Path) -> dict[int, str]:
    """Map migration index → basename for SQL files on ``ref``."""
    try:
        rel = migrations_dir.relative_to(cwd).as_posix()
    except ValueError:
        rel = migrations_dir.as_posix()
    result = _run_git(["ls-tree", "-r", "--name-only", ref, "--", rel], cwd=cwd)
    if result.returncode != 0:
        return {}
    out: dict[int, str] = {}
    for line in result.stdout.splitlines():
        name = Path(line.strip()).name
        parsed = _parse_index_suffix(name)
        if parsed:
            out[parsed[0]] = name
    return out


def _fix_dir(
    migrations_dir: Path,
    *,
    cwd: Path,
    integration_ref: str,
) -> MigrationFixResult:
    result = MigrationFixResult()
    sql_files = [
        p for p in migrations_dir.iterdir()
        if p.is_file() and MIGRATION_SQL_NAME.match(p.name)
    ]
    if not sql_files:
        return result

    by_index: dict[int, list[Path]] = defaultdict(list)
    for path in sql_files:
        parsed = _parse_index_suffix(path.name)
        if parsed:
            by_index[parsed[0]].append(path)

    on_main_names = _files_on_ref(integration_ref, migrations_dir, cwd=cwd)
    main_by_index = _indexes_on_ref(integration_ref, migrations_dir, cwd=cwd)

    # Virtual collisions: ticket has NNNN_foo while main has NNNN_bar (different
    # basename). Renumber the ticket file only — do not materialize main's SQL.
    virtual_renames: list[Path] = []
    used_indexes = set(by_index.keys()) | set(main_by_index.keys())
    for idx, main_name in sorted(main_by_index.items()):
        local_files = list(by_index.get(idx, []))
        for local in local_files:
            if local.name == main_name:
                continue
            if local.name in on_main_names:
                continue
            virtual_renames.append(local)

    meta_dir = migrations_dir / "meta"
    journal = _load_journal(meta_dir)
    entries: list[dict] = list(journal.get("entries") or [])
    entries_by_tag = {
        str(e.get("tag") or ""): e for e in entries if isinstance(e, dict)
    }

    def _renumber_file(path: Path, old_index: int) -> None:
        nonlocal used_indexes, entries_by_tag
        parsed = _parse_index_suffix(path.name)
        if not parsed or not path.exists():
            return
        _old_idx, suffix = parsed
        new_index = _next_free_index(used_indexes)
        used_indexes.add(new_index)
        new_name = f"{new_index:04d}_{suffix}.sql"
        new_path = migrations_dir / new_name
        if new_path.exists():
            result.messages.append(f"skip rename {path.name}: target {new_name} exists")
            return
        old_rel = path.as_posix()
        path.rename(new_path)
        result.renames.append((old_rel, new_path.as_posix()))
        result.changed = True
        result.messages.append(f"renamed {path.name} → {new_name}")
        old_tag = f"{old_index:04d}_{suffix}"
        new_tag = f"{new_index:04d}_{suffix}"
        entry = entries_by_tag.get(old_tag)
        if entry is not None:
            entry["tag"] = new_tag
            entry["idx"] = new_index
            entries_by_tag.pop(old_tag, None)
            entries_by_tag[new_tag] = entry
        else:
            for e in entries:
                if not isinstance(e, dict):
                    continue
                if int(e.get("idx", -1)) == old_index and str(e.get("tag") or "").endswith(
                    f"_{suffix}"
                ):
                    e["tag"] = new_tag
                    e["idx"] = new_index
                    break
            else:
                entries.append(
                    {
                        "idx": new_index,
                        "version": "7",
                        "when": 0,
                        "tag": new_tag,
                        "breakpoints": True,
                    }
                )
        if meta_dir.is_dir():
            _copy_snapshot_for_new_index(meta_dir, old_index, new_index)
        # Refresh by_index for subsequent on-disk collision pass
        by_index[old_index] = [p for p in by_index.get(old_index, []) if p != path]
        by_index[new_index].append(new_path)

    for path in virtual_renames:
        parsed = _parse_index_suffix(path.name)
        if parsed:
            _renumber_file(path, parsed[0])

    # Recompute on-disk collisions after virtual renames
    by_index = defaultdict(list)
    for path in migrations_dir.iterdir():
        if path.is_file() and MIGRATION_SQL_NAME.match(path.name):
            parsed = _parse_index_suffix(path.name)
            if parsed:
                by_index[parsed[0]].append(path)

    collisions = {idx: files for idx, files in by_index.items() if len(files) >= 2}
    on_main = on_main_names
    used_indexes = set(by_index.keys()) | set(main_by_index.keys())

    for old_index in sorted(collisions):
        files = sorted(collisions[old_index], key=lambda p: p.name)
        keep: Path | None = None
        for path in files:
            if path.name in on_main:
                keep = path
                break
        if keep is None:
            keep = files[0]
            result.messages.append(
                f"{migrations_dir.as_posix()}: no {old_index:04d}_* on {integration_ref}; "
                f"keeping {keep.name} and renumbering siblings"
            )

        for path in files:
            if path == keep:
                continue
            _renumber_file(path, old_index)

    if not result.changed and not collisions and not virtual_renames:
        return result

    if result.changed:
        present_tags: set[str] = set()
        for path in migrations_dir.iterdir():
            if not path.is_file():
                continue
            parsed = _parse_index_suffix(path.name)
            if parsed:
                present_tags.add(f"{parsed[0]:04d}_{parsed[1]}")
        cleaned: list[dict] = []
        seen_idx: set[int] = set()
        for e in sorted(
            (x for x in entries if isinstance(x, dict)),
            key=lambda x: int(x.get("idx", 0)),
        ):
            tag = str(e.get("tag") or "")
            idx = int(e.get("idx", -1))
            if tag and tag not in present_tags:
                continue
            if idx in seen_idx:
                continue
            e["idx"] = idx
            cleaned.append(e)
            seen_idx.add(idx)
        for path in sorted(migrations_dir.iterdir()):
            parsed = _parse_index_suffix(path.name) if path.is_file() else None
            if not parsed:
                continue
            idx, suffix = parsed
            tag = f"{idx:04d}_{suffix}"
            if any(str(e.get("tag")) == tag for e in cleaned):
                continue
            cleaned.append(
                {
                    "idx": idx,
                    "version": "7",
                    "when": 0,
                    "tag": tag,
                    "breakpoints": True,
                }
            )
        for e in cleaned:
            tag = str(e.get("tag") or "")
            m = re.match(r"^(\d{4})_", tag)
            if m:
                e["idx"] = int(m.group(1))
        cleaned.sort(key=lambda x: int(x.get("idx", 0)))
        journal["entries"] = cleaned
        _save_journal(meta_dir, journal)
        _relink_snapshot_prev_ids(meta_dir)

    return result


def fix_duplicate_migration_indexes(
    root: Path | None = None,
    *,
    integration_ref: str = "origin/main",
    cwd: Path | None = None,
) -> MigrationFixResult:
    """Fix all duplicate ``NNNN_*.sql`` collisions under ``root``.

    Keeps SQL files that already exist on ``integration_ref``; renumbers the
    ticket's colliding files to the next free indexes and aligns journal/snapshots.
    """
    base = (root or Path.cwd()).resolve()
    git_cwd = (cwd or base).resolve()
    aggregate = MigrationFixResult()

    # Fetch is best-effort — caller may already have fetched.
    _run_git(["fetch", "origin", "--prune"], cwd=git_cwd)

    for migrations_dir in _migration_dirs(base):
        partial = _fix_dir(
            migrations_dir,
            cwd=git_cwd,
            integration_ref=integration_ref,
        )
        if partial.changed:
            aggregate.changed = True
        aggregate.renames.extend(partial.renames)
        aggregate.messages.extend(partial.messages)

    if not aggregate.changed:
        aggregate.messages.append(aggregate.summary)
    else:
        logger.info("migration_index_fix: %s", aggregate.summary)
    return aggregate


def migrations_only_conflict_paths(paths: list[str]) -> bool:
    """True when every path is under a ``migrations/`` tree (or empty)."""
    if not paths:
        return False
    for path in paths:
        parts = Path(path).parts
        if "migrations" not in parts:
            return False
    return True


# Signals that a ticket is likely to write Drizzle/ORM migrations (schema hotspot).
SCHEMA_HOTSPOT_RE = re.compile(
    r"(?is)"
    r"(?:\bdrizzle\b|"
    r"\bmigrations?/(?:meta/)?|"
    r"\b_journal\.json\b|"
    r"\bschema\s+migration\b|"
    r"\b(?:db|database|sql)\s+migration\b|"
    r"\balembic\b|"
    r"\badd(?:ing)?\s+(?:a\s+)?migration\b|"
    r"\bnew\s+migration\b|"
    r"apps/api/migrations\b)"
)


def text_suggests_schema_hotspot(text: str | None) -> bool:
    """True when ticket/plan prose suggests the ticket will touch migrations."""
    if not text or not str(text).strip():
        return False
    return SCHEMA_HOTSPOT_RE.search(str(text)) is not None


def worktree_has_migration_changes(
    cwd: Path,
    *,
    integration_ref: str = "origin/main",
) -> bool:
    """True when the worktree differs from ``integration_ref`` under ``migrations/``."""
    work = Path(cwd)
    for args in (
        ["diff", "--name-only", f"{integration_ref}...HEAD"],
        ["diff", "--name-only", "--cached"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        result = _run_git(args, cwd=work)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            parts = Path(line.strip()).parts
            if "migrations" in parts:
                return True
    return False


def _list_unmerged_paths(*, cwd: Path) -> list[str]:
    result = _run_git(
        ["diff", "--name-only", "--diff-filter=U", "-z"],
        cwd=cwd,
    )
    if result.returncode != 0:
        # Fallback without -z
        result = _run_git(
            ["diff", "--name-only", "--diff-filter=U"],
            cwd=cwd,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    raw = result.stdout
    if "\0" in raw:
        return [p for p in raw.split("\0") if p]
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _rebase_in_progress(*, cwd: Path) -> bool:
    merge = _run_git(["rev-parse", "--git-path", "rebase-merge"], cwd=cwd)
    apply = _run_git(["rev-parse", "--git-path", "rebase-apply"], cwd=cwd)
    for proc in (merge, apply):
        if proc.returncode != 0:
            continue
        path = Path(proc.stdout.strip())
        if not path.is_absolute():
            path = cwd / path
        if path.exists():
            return True
    return False


def _checkout_migration_side(
    path: str,
    *,
    prefer_upstream: bool,
    cwd: Path,
) -> None:
    preferred = "--ours" if prefer_upstream else "--theirs"
    fallback = "--theirs" if prefer_upstream else "--ours"
    result = _run_git(["checkout", preferred, "--", path], cwd=cwd)
    if result.returncode != 0:
        _run_git(["checkout", fallback, "--", path], cwd=cwd)


def prepare_migrations_for_mechanical_fix(
    conflicted: list[str],
    integration_ref: str,
    *,
    cwd: Path,
    log: Callable[[str], None] | None = None,
) -> None:
    """Clear conflict markers on migration paths so the mechanical fixer can run.

    During rebase, ``--ours`` is upstream (main). Keep upstream for journal /
    snapshots / SQL already on main; keep the ticket side for new ticket SQL.
    """
    work = Path(cwd)
    main_sql: set[str] = set()
    listed = _run_git(["ls-tree", "-r", "--name-only", integration_ref, "--"], cwd=work)
    if listed.returncode == 0:
        for line in listed.stdout.splitlines():
            line = line.strip()
            if "/migrations/" in line.replace("\\", "/") and line.endswith(".sql"):
                main_sql.add(Path(line).name)

    for path in conflicted:
        parts = Path(path).parts
        if "migrations" not in parts:
            continue
        name = Path(path).name
        if name.endswith(".sql"):
            prefer_upstream = name in main_sql
        else:
            prefer_upstream = True
        _checkout_migration_side(path, prefer_upstream=prefer_upstream, cwd=work)
        if log:
            side = "ours" if prefer_upstream else "theirs"
            log(f"migration pre-fix checkout {side} for {path}")


def _stage_migration_paths(paths: list[str], *, cwd: Path) -> list[str]:
    staged = list(dict.fromkeys(paths))
    for path in paths:
        parts = Path(path).parts
        if "migrations" not in parts:
            continue
        idx = parts.index("migrations")
        root = str(Path(*parts[: idx + 1]))
        if root not in staged:
            staged.append(root)
    return staged


def heal_migrations_only_rebase_conflict(
    *,
    ticket_id: str,
    conflicted: list[str],
    integration_ref: str,
    cwd: Path | str,
    log: Callable[[str], None] | None = None,
    max_passes: int = 8,
) -> tuple[bool, list[str]]:
    """Mechanically resolve migrations-only rebase conflicts and continue.

    Returns ``(ok, remaining_conflicted)``. ``ok=True`` means the rebase finished
    (or was already clean). On failure, returns the current unmerged paths and
    leaves the rebase in progress for the conflict-resolver / human.
    """
    work = Path(cwd)
    _log = log or (lambda _msg: None)
    current = list(conflicted)
    if not current:
        current = _list_unmerged_paths(cwd=work)
    if not current:
        return (not _rebase_in_progress(cwd=work)), []

    for pass_idx in range(1, max_passes + 1):
        if not migrations_only_conflict_paths(current):
            _log(
                f"{ticket_id}: migration heal pass {pass_idx}: "
                f"non-migration conflicts remain ({len(current)})"
            )
            return False, current

        _log(
            f"{ticket_id}: migration heal pass {pass_idx}/{max_passes}: "
            f"migrations-only ({len(current)} paths)"
        )
        prepare_migrations_for_mechanical_fix(
            current, integration_ref, cwd=work, log=lambda m: _log(f"{ticket_id}: {m}"),
        )
        result = fix_duplicate_migration_indexes(
            work, integration_ref=integration_ref, cwd=work,
        )
        _log(f"{ticket_id}: migration heal: {result.summary}")

        paths_to_stage = list(current)
        for src, dst in result.renames:
            paths_to_stage.append(src)
            paths_to_stage.append(dst)
        staged = _stage_migration_paths(paths_to_stage, cwd=work)
        if staged:
            add = _run_git(["add", "--"] + staged, cwd=work)
            if add.returncode != 0:
                _log(
                    f"{ticket_id}: migration heal git add failed: "
                    f"{(add.stderr or add.stdout or '').strip()}"
                )
                return False, current

        env = dict(os.environ)
        env["GIT_EDITOR"] = "true"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cont = subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=str(work),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        combined = ((cont.stdout or "") + (cont.stderr or "")).lower()
        if cont.returncode != 0 and "nothing to commit" in combined:
            skip = _run_git(["rebase", "--skip"], cwd=work)
            if skip.returncode != 0:
                _log(
                    f"{ticket_id}: migration heal rebase --skip failed: "
                    f"{(skip.stderr or skip.stdout or '').strip()}"
                )
                return False, _list_unmerged_paths(cwd=work) or current
        elif cont.returncode != 0:
            current = _list_unmerged_paths(cwd=work)
            if current and migrations_only_conflict_paths(current):
                continue
            _log(
                f"{ticket_id}: migration heal rebase --continue failed: "
                f"{(cont.stderr or cont.stdout or '').strip()}"
            )
            return False, current or conflicted

        if not _rebase_in_progress(cwd=work):
            _log(f"{ticket_id}: migration heal: rebase completed")
            return True, []

        current = _list_unmerged_paths(cwd=work)
        if not current:
            # Still rebasing but no conflicts yet — keep continuing empty?
            # Leave for caller if somehow stuck.
            if not _rebase_in_progress(cwd=work):
                return True, []
            continue

    _log(f"{ticket_id}: migration heal exhausted {max_passes} passes")
    return False, _list_unmerged_paths(cwd=work) or conflicted


__all__ = [
    "MIGRATION_SQL_NAME",
    "SCHEMA_HOTSPOT_RE",
    "MigrationFixResult",
    "duplicate_migration_path_groups",
    "find_duplicate_migration_indexes",
    "fix_duplicate_migration_indexes",
    "heal_migrations_only_rebase_conflict",
    "list_migration_sql_files",
    "migrations_only_conflict_paths",
    "prepare_migrations_for_mechanical_fix",
    "text_suggests_schema_hotspot",
    "worktree_has_migration_changes",
]
