"""Tests for mechanical Drizzle migration index renumbering."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

from migration_index_fix import (
    find_duplicate_migration_indexes,
    fix_duplicate_migration_indexes,
    migrations_only_conflict_paths,
)


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@test"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, capture_output=True)


def _commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, capture_output=True, check=True)


def _write_journal(meta: Path, tags: list[str]) -> None:
    meta.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "idx": i,
            "version": "7",
            "when": 1000 + i,
            "tag": tag,
            "breakpoints": True,
        }
        for i, tag in enumerate(tags)
    ]
    (meta / "_journal.json").write_text(
        json.dumps({"version": "7", "dialect": "postgresql", "entries": entries}, indent=4)
        + "\n",
        encoding="utf-8",
    )


def _write_snapshot(meta: Path, index: int, snap_id: str, prev_id: str | None) -> None:
    meta.mkdir(parents=True, exist_ok=True)
    data = {"id": snap_id, "prevId": prev_id, "version": "7", "tables": {}}
    (meta / f"{index:04d}_snapshot.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8",
    )


def test_no_collision_is_noop(tmp_path: Path):
    mig = tmp_path / "apps" / "api" / "migrations"
    mig.mkdir(parents=True)
    (mig / "0004_wild_legion.sql").write_text("ALTER TABLE a;\n")
    (mig / "0005_careless.sql").write_text("CREATE TABLE b;\n")
    _write_journal(mig / "meta", ["0004_wild_legion", "0005_careless"])

    _git_init(tmp_path)
    _commit_all(tmp_path, "init")
    # origin/main alias: create local main branch ref used as integration
    subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    result = fix_duplicate_migration_indexes(
        tmp_path, integration_ref="origin/main", cwd=tmp_path,
    )
    assert result.changed is False
    assert (mig / "0004_wild_legion.sql").exists()
    assert (mig / "0005_careless.sql").exists()
    assert find_duplicate_migration_indexes(tmp_path) == []


def test_on_disk_collision_renumbers_ticket_file(tmp_path: Path):
    mig = tmp_path / "apps" / "api" / "migrations"
    mig.mkdir(parents=True)
    (mig / "0004_wild_legion.sql").write_text("ALTER TABLE movies;\n")
    (mig / "0004_careless_moon_knight.sql").write_text("CREATE TABLE profiles;\n")
    meta = mig / "meta"
    _write_journal(meta, ["0004_wild_legion", "0004_careless_moon_knight"])
    _write_snapshot(meta, 4, "id-main-4", "id-3")

    _git_init(tmp_path)
    # First commit only main's migration so ls-tree on origin/main sees it
    subprocess.run(["git", "add", "apps/api/migrations/0004_wild_legion.sql"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "add", "apps/api/migrations/meta"],
        cwd=tmp_path,
        capture_output=True,
    )
    # Temporarily hide ticket file from first commit
    ticket = mig / "0004_careless_moon_knight.sql"
    content = ticket.read_text()
    ticket.unlink()
    _commit_all(tmp_path, "main migration")
    subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    ticket.write_text(content)
    _write_journal(meta, ["0004_wild_legion", "0004_careless_moon_knight"])

    result = fix_duplicate_migration_indexes(
        tmp_path, integration_ref="origin/main", cwd=tmp_path,
    )
    assert result.changed is True
    assert (mig / "0004_wild_legion.sql").exists()
    assert not (mig / "0004_careless_moon_knight.sql").exists()
    assert (mig / "0005_careless_moon_knight.sql").exists()
    assert find_duplicate_migration_indexes(tmp_path) == []

    journal = json.loads((meta / "_journal.json").read_text())
    tags = [e["tag"] for e in journal["entries"]]
    assert "0004_wild_legion" in tags
    assert "0005_careless_moon_knight" in tags
    assert "0004_careless_moon_knight" not in tags


def test_virtual_collision_against_main_renumbers_before_pr(tmp_path: Path):
    """Ticket only has 0004_ticket; main has 0004_main — renumber ticket to 0005."""
    mig = tmp_path / "apps" / "api" / "migrations"
    mig.mkdir(parents=True)
    (mig / "0004_wild_legion.sql").write_text("ALTER TABLE movies;\n")
    meta = mig / "meta"
    _write_journal(meta, ["0004_wild_legion"])
    _write_snapshot(meta, 4, "id-4", None)

    _git_init(tmp_path)
    _commit_all(tmp_path, "main")
    subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Simulate ticket branch: replace with ticket migration only
    (mig / "0004_wild_legion.sql").unlink()
    (mig / "0004_right_mantis.sql").write_text("CREATE TABLE title_match;\n")
    _write_journal(meta, ["0004_right_mantis"])

    result = fix_duplicate_migration_indexes(
        tmp_path, integration_ref="origin/main", cwd=tmp_path,
    )
    assert result.changed is True
    assert not (mig / "0004_right_mantis.sql").exists()
    assert (mig / "0005_right_mantis.sql").exists()
    # Must not materialize main's file onto the ticket branch
    assert not (mig / "0004_wild_legion.sql").exists()

    journal = json.loads((meta / "_journal.json").read_text())
    tags = [e["tag"] for e in journal["entries"]]
    assert tags == ["0005_right_mantis"]


def test_migrations_only_conflict_paths():
    assert migrations_only_conflict_paths(
        ["apps/api/migrations/0004_a.sql", "apps/api/migrations/meta/_journal.json"]
    )
    assert not migrations_only_conflict_paths(
        ["apps/api/migrations/0004_a.sql", "apps/api/src/index.ts"]
    )
    assert not migrations_only_conflict_paths([])


def test_pr_lifecycle_calls_migration_fix(tmp_path: Path, monkeypatch):
    import ticket_pr_lifecycle as tpl

    calls: list[str] = []

    class FakeResult:
        changed = True
        summary = "renamed 1 migration(s)"
        messages = ["renamed 0004_x.sql → 0005_x.sql"]
        renames = [("a", "b")]

    def fake_fix(root, integration_ref="origin/main", cwd=None):
        calls.append(f"fix:{integration_ref}")
        return FakeResult()

    monkeypatch.setattr(
        "migration_index_fix.fix_duplicate_migration_indexes",
        fake_fix,
    )

    def fake_fetch(*_a, **_k):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(tpl.subprocess, "run", fake_fetch)

    checkpoints: list[str] = []

    def fake_checkpoint(ticket_id, message, **_kwargs):
        checkpoints.append(message)

    monkeypatch.setattr(tpl, "checkpoint_transition", fake_checkpoint)
    monkeypatch.setattr(tpl, "resolve_integration_branch", lambda *_a, **_k: "main")
    monkeypatch.setattr(tpl, "rebase_onto_ref", lambda b: f"origin/{b}")
    monkeypatch.setattr(tpl, "_log", lambda *_a, **_k: None)

    run_dir = tmp_path / "runs" / "T011"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}")

    changed = tpl._fix_migration_indexes_before_pr("T011", run_dir, cwd=str(tmp_path))
    assert changed is True
    assert calls == ["fix:origin/main"]
    assert any("renumber migrations" in m for m in checkpoints)


def test_text_suggests_schema_hotspot():
    from migration_index_fix import text_suggests_schema_hotspot

    assert text_suggests_schema_hotspot("Add drizzle migration under apps/api/migrations/")
    assert text_suggests_schema_hotspot("Update _journal.json for the new schema")
    assert not text_suggests_schema_hotspot("Build a React settings page")


def test_migrations_only_conflict_paths_helper():
    from migration_index_fix import migrations_only_conflict_paths

    assert migrations_only_conflict_paths(
        ["apps/api/migrations/0008_x.sql", "apps/api/migrations/meta/_journal.json"]
    )
    assert not migrations_only_conflict_paths(
        ["apps/api/migrations/0008_x.sql", "apps/api/src/services/catalog-sync-service.ts"]
    )
