# Plan fix — include Postgres runtime DB coverage for Ticket Intelligence lifecycle fields

## Required plan update

Update `runs/T208/plan.md` before implementation starts.

The plan must not only update the SQLite runtime database implementation.

It must also verify and update the Postgres runtime database implementation when it owns the same `ticket_intelligence` persistence path.

## New lifecycle fields

T208 introduces these fields:

```text
started_at
completed_at
failed_at
failure_origin
```

They must be consistently supported across runtime DB implementations.

## SQLite path

Already planned:

```text
tools/agent_runner/runtime_db.py
```

Keep the existing SQLite plan:

- introspect `PRAGMA table_info('ticket_intelligence')`
- add missing columns idempotently
- persist fields through `upsert_ticket_intelligence`
- return fields through read helpers

## Postgres path

Add explicit coverage for:

```text
tools/agent_runner/runtime_db_pg.py
```

Required behavior:

1. If `ticket_intelligence` is defined in `runtime_db_pg.py`, add the same columns:

```sql
started_at TEXT
completed_at TEXT
failed_at TEXT
failure_origin TEXT
```

or the equivalent Postgres-compatible column types already used by the project.

2. Use idempotent Postgres migration syntax, for example:

```sql
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS started_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS completed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failure_origin TEXT;
```

3. Ensure Postgres upsert logic persists these fields.

4. Ensure Postgres read/list helpers return these fields.

5. Ensure API schema compatibility remains identical whether the runtime DB is SQLite or Postgres.

## Tests / acceptance criteria

Add at least one of the following:

### Preferred

A focused Postgres runtime DB unit test if the project already has PG test infrastructure.

Example:

```text
test_pg_ticket_intelligence_lifecycle_fields_are_created_and_round_trip
```

### Acceptable fallback

If no PG test infrastructure exists, add explicit acceptance criteria and comments near `runtime_db_pg.py` changes explaining that:

- Postgres schema creation includes the fields
- Postgres upsert accepts the fields
- Postgres read helpers return the fields
- SQLite and Postgres expose the same public Ticket Intelligence shape

## Acceptance criteria additions

Add these to the corrected plan:

- `runtime_db_pg.py` is checked for `ticket_intelligence` support.
- If Postgres stores Ticket Intelligence, it includes `started_at`, `completed_at`, `failed_at`, and `failure_origin`.
- SQLite and Postgres Ticket Intelligence persistence expose the same lifecycle fields.
- The API `TicketIntelligence` schema remains backend-agnostic.
- Tests or explicit acceptance criteria cover the Postgres path.

## Non-goals reminder

Do not introduce a new database abstraction layer in T208.

Do not migrate historical rows.

Do not change the reaper thresholds.

Do not replace the existing background execution model with a queue system.
