# Plan Review — T159

## Verdict

The plan is directionally correct and should proceed, but it needs one important correction before implementation: SQLite recovery/quarantine must be protected by an explicit file lock.

## What is good

The plan correctly targets the current operational pain:

- runtime SQLite corruption can block the board and daemon
- the board needs degraded-mode visibility
- the daemon needs startup integrity checks
- SQLite needs safer defaults
- accidental DB creation under worktrees/clones must be audited

The following items are good and should remain in scope:

- `PRAGMA integrity_check` at startup
- automatic quarantine of corrupted DBs
- fallback to recovery or empty DB recreation
- `busy_timeout=5000`
- `synchronous=NORMAL`
- `sqlite_degraded` flag in `BoardResponse`
- dashboard degraded-mode banner
- read-only audit for secondary DB paths

## Required correction

The plan currently states or implies that POSIX atomic rename makes `check_and_recover_db()` safe for concurrent callers.

That is not sufficient.

Atomic rename only protects the rename operation itself. The full recovery sequence is a multi-step critical section:

```text
integrity_check
→ decide DB is corrupted
→ quarantine DB
→ recover or recreate DB
→ initialize schema
```

If two daemon/API processes execute this at the same time, they can race and corrupt or overwrite the recovery result.

## Required plan change

Add an explicit file-lock guard around `check_and_recover_db(db_path)`.

Recommended lock path:

```text
<db_path>.recovery.lock
```

The lock must be acquired before:

- opening the DB for integrity check
- quarantining the corrupted DB
- attempting recovery
- recreating an empty DB
- initializing schema

The lock must be released after the recovery/recreate path completes.

## Acceptance criteria to add

- Concurrent calls to `check_and_recover_db()` cannot quarantine/recreate the same DB simultaneously.
- Recovery/quarantine is protected by a file lock.
- Tests cover two recovery attempts hitting the same DB path.

## Final recommendation

Approve the plan after adding the lock-file correction.
