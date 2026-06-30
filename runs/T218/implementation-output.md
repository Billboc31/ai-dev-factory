## Summary

Closed the B1 Postgres-backend gap raised by review.

### Changes

**`tools/agent_runner/runtime_db_pg.py`**
- `_DDL`: added the three new tables — `backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis` — each carrying a `project_id` column at the front of every composite PK so row-level project isolation is enforced for the single shared `adf` database (same invariant as the rest of this module).
- `UNIQUE(project_id, ticket_id)` on `backlog_batch_tickets` so a ticket cannot be a member of two batches at once within a project — this is what `insert_backlog_batch_ticket` keys off of via `ON CONFLICT DO NOTHING`.
- Implemented the 9 helpers mirroring the SQLite contract one-for-one: `insert_backlog_batch`, `get_backlog_batch`, `list_backlog_batches`, `update_backlog_batch`, `insert_backlog_batch_ticket` (returns `False` on conflict via `cur.rowcount==0`, no driver-exception coupling), `list_backlog_batch_ticket_ids`, `get_batch_for_ticket`, `upsert_dependency_analysis` (PG `ON CONFLICT (project_id, ticket_id, batch_id) DO UPDATE`), `get_dependency_analysis` (decodes the four `_json` columns into Python lists, dropping the suffix).

**`tools/agent_runner/runtime_db.py`**
- Added the 9 `_pg.*` rebinds at the end of the `if _RUNTIME_DB_BACKEND == "postgres":` block.

**`tests/test_runtime_db_pg.py`**
- 16 new tests covering DDL declaration, project-id scoping on every helper, `ON CONFLICT DO NOTHING` true/false branches, JSON encode/decode round-trip, and a final test that loads `runtime_db.py` under `RUNTIME_DB_BACKEND=postgres` and asserts all 9 helpers' `__module__` resolves to `runtime_db_pg`.

### Verification
- New PG smoke tests: 33 passed (16 new + 17 pre-existing).
- T218 SQLite suites unchanged: 42 passed across `test_backlog_batch`, `test_global_dependency_analyzer`, `test_daemon_batch_lifecycle`, `test_ticket_readiness_evaluator`.
- The one PG test that fails (`test_default_backend_is_sqlite`) is pre-existing — unrelated to this fix (asserts a `TypeError` that SQLite's `get_db_path(project_id=…)` no longer raises).
