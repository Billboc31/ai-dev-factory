# Plan review — T208 must cover Postgres runtime DB

The T208 plan is directionally correct and addresses the observed failure mode: Ticket Intelligence analyses can remain stuck in `running` until the 900s reaper marks them failed.

The plan correctly includes:

- hardening background thread exception handling
- bounding AI subprocess execution with explicit timeout and kill
- persisting terminal failure states
- adding lifecycle timestamps
- improving reaper behavior
- adding structured logs and tests

However, the plan currently only describes schema/persistence changes for the SQLite runtime DB:

```text
tools/agent_runner/runtime_db.py
```

This is incomplete because AI Dev Factory also has a Postgres runtime DB path:

```text
tools/agent_runner/runtime_db_pg.py
```

If T208 adds these fields only to SQLite:

```text
started_at
completed_at
failed_at
failure_origin
```

then Ticket Intelligence may work in SQLite but fail or silently lose data in Postgres-backed runtimes.

## Blocking issue

The plan must explicitly verify and update the Postgres implementation for the `ticket_intelligence` table and related upsert/select helpers.

Required coverage:

1. Add the same columns to Postgres schema initialization if `ticket_intelligence` exists there.
2. Ensure idempotent schema migration for existing Postgres databases.
3. Ensure `upsert_ticket_intelligence` / read helpers persist and return the new fields.
4. Ensure API schema exposure remains compatible across both SQLite and Postgres runtimes.
5. Add at least one test or acceptance criterion that validates Postgres compatibility.

## Required correction

Update `runs/T208/plan.md` so that:

- `tools/agent_runner/runtime_db_pg.py` is included in the files modified if it owns the Postgres ticket intelligence schema.
- Postgres schema initialization/migration includes `started_at`, `completed_at`, `failed_at`, and `failure_origin`.
- Postgres persistence/read paths are verified for the new fields.
- Tests or acceptance criteria explicitly cover the Postgres path.

## Review verdict

PLAN_FIX_REQUIRED until Postgres runtime DB coverage is explicitly included or explicitly proven unnecessary.
