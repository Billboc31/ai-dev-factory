# T159 — T159 - Harden runtime SQLite architecture and degraded-mode recovery

**Source**: GitHub Issue #166

## Description

# T159 - Harden runtime SQLite architecture and degraded-mode recovery

## Problem

The runtime SQLite database regularly becomes corrupted (`database disk image is malformed`) and currently blocks:

- runtime dashboard visibility
- daemon ticket synchronization
- environment visibility
- runtime observability
- ticket execution flow

The current architecture is too fragile because runtime visibility depends too heavily on a single SQLite file.

---

# Goals

- Make the runtime platform resilient to SQLite corruption
- Ensure the Runtime dashboard remains usable even if SQLite fails
- Move toward a single global runtime database architecture
- Reduce corruption probability significantly
- Improve daemon/runtime recovery behavior

---

# Included

## Global runtime database architecture

Move toward:

```text
~/runtime/ai-dev-factory/.runtime/ai-dev-factory.sqlite
```

Rules:

- single runtime DB per ai-dev-factory instance
- worktrees must NOT create their own runtime DBs
- clone-local runtime DBs should be avoided
- runtime state becomes globally indexed

The runtime DB becomes:

- metadata/index/cache layer
- historical/runtime coordination layer

NOT the sole source of truth.

---

## Filesystem-first runtime architecture

The Runtime dashboard and environment visibility must continue functioning without SQLite.

Filesystem runtime state becomes the primary truth source:

```text
runtime/
  sandboxes/
    <sandbox-id>/
      state.json
      validation.json
      logs/
  proxy/routes/
  worktrees/
```

If SQLite fails:

- Runtime UI still renders environments
- sandboxes still appear
- routes still appear
- validation state still appears
- a degraded-mode warning is shown

---

## SQLite degraded-mode fallback

If SQLite access fails:

- log explicit corruption warning
- rename broken DB automatically
- recreate clean DB if possible
- continue runtime in degraded mode
- avoid daemon crash loops

Example:

```text
runtime DB corrupted -> entering degraded mode
```

---

## SQLite startup integrity checks

At startup:

```sql
PRAGMA integrity_check;
```

If integrity check fails:

- quarantine broken DB
- optionally attempt `.recover`
- recreate empty DB if recovery impossible
- continue degraded runtime mode

---

## SQLite hardening pragmas

Enable safer defaults:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;
```

Evaluate additional pragmas if needed.

---

## Single-writer protections

Add protections against multiple daemon writers:

- startup lock file
- daemon singleton guard
- clearer logs when another daemon already exists
- prevent concurrent SQLite writers when possible

---

## Runtime dashboard degraded UX

Runtime UI should display:

```text
SQLite runtime database unavailable
Showing filesystem-derived runtime state
```

The platform should remain observable.

---

## Cleanup of legacy runtime DB locations

Audit and remove accidental DB creation in:

```text
worktrees/*/.runtime/
clones/*/.runtime/
```

Ensure runtime DB path resolution is deterministic and centralized.

---

# Excluded

- No PostgreSQL migration
- No distributed runtime coordination
- No multi-user runtime synchronization
- No HA/replication architecture
- No cloud database support
- No Kubernetes persistence layer

---

# Acceptance criteria

- Runtime dashboard still works if SQLite becomes corrupted
- Daemon does not enter infinite crash/retry loops on malformed DB
- Runtime state remains observable through filesystem fallback
- Only one global runtime DB is used
- Worktrees no longer create runtime SQLite DBs
- SQLite corruption probability is significantly reduced
- Startup integrity checks run automatically
- Broken DBs are quarantined automatically
- Users receive explicit degraded-mode warnings
- Existing deploy/sandbox/runtime flows continue functioning
