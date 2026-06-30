# Review — T218 (attempt 2)

## Summary

This pass closes the single blocking issue from review attempt 1 (B1 — Postgres backend gap) and re-verifies the rest of the implementation against the plan and acceptance criteria. The implementation now satisfies the plan on **both** SQLite and Postgres backends, with the contract-parity verified at the bind-site level.

## Verification against attempt-1 blocker (B1)

The Postgres backend gap is closed in three places:

- `tools/agent_runner/runtime_db_pg.py:246-292` — `_DDL` declares the three new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`) with `project_id` first in every composite primary key, and `UNIQUE(project_id, ticket_id)` on `backlog_batch_tickets`.
- `tools/agent_runner/runtime_db_pg.py:1193-1418` — all nine helpers implemented with parameterised `WHERE project_id = %s` scoping and PG-native `ON CONFLICT … DO UPDATE` / `DO NOTHING`. `insert_backlog_batch_ticket` returns `False` via `cur.rowcount == 0` (no driver-exception coupling), matching the SQLite contract.
- `tools/agent_runner/runtime_db.py:1483-1492` — the postgres rebind block rebinds all nine names to `_pg.*`.

`tests/test_runtime_db_pg.py:265-500` adds 18 tests covering DDL, project isolation, `ON CONFLICT` true/false branches, JSON round-trip, and a rebind-site assertion (`__module__ == "runtime_db_pg"`).

## Plan coverage (re-check)

- **State machine**: 7 statuses, no `pending_collecting`; guarded transitions raise `BatchTransitionError`; `batch.dependency_analysis_exhausted` emitted exactly once on attempts == max_attempts.
- **Parallel-batch policy**: `freeze_blocked` flag only (no new status), cleared by `unblock_freezing_for_pending_collecting_batches` when no `dispatching` batch remains.
- **Dispatcher gate**: `ticket_dispatcher._ticket_passes_batch_gate` (lines 217-238) excludes non-`dispatching` batch members; legacy non-batch tickets unaffected.
- **Readiness gate**: `ticket_pipeline._is_batch_ready_for_readiness` gates readiness on batch status ≥ `readiness_running`; dependency union extended in `collect_dependency_ticket_ids` to consume `ticket_dependency_analysis.depends_on`.
- **Daemon integration**: `process_backlog_batches` runs once per cycle (verified by `test_main_once_calls_process_backlog_batches`).
- **Settings**: six `BACKLOG_*` keys registered with sane defaults.

## Test results

- New T218 suites + PG smoke tests: **75/76 passed**. The one PG failure (`test_default_backend_is_sqlite`) was confirmed pre-existing on `main`, unrelated to T218.
- Full repo suite (excluding PG tests): 128 failed / 1847 passed / 14 errored — identical baseline to `main`, so no new failures introduced.

## Non-blocking observations

- **O2** (orphan-state risk if a ticket fails-final without `daemon_archived=1`) and **O3** (`runs/T218/fixes/` workflow noise) carry over from attempt 1.
- **O4**: `global_dependency_analyzer._INLINE_PROMPT` duplicates the schema in `prompts/global-dependency-analyzer-prompt.md`. Worth a comment that the markdown file is the source of truth.

## Verdict

Plan-defined behaviour now correctly implemented on both SQLite and Postgres backends. Previous blocker fully closed with targeted tests. No regression in the existing test surface.

IMPLEMENTATION_APPROVED
