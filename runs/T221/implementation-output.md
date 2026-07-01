Implementation is complete. Here is the summary.

## Summary of Changes

### Files modified
- **`tools/agent_runner/runtime_settings.py`** — Registered 4 new settings (`GITHUB_POLL_INTERVAL_SECONDS`, `MAX_ISSUES_INTAKED_PER_POLL`, `MAX_PARALLEL_TICKET_INTELLIGENCE`, `MAX_PARALLEL_READINESS`) with DB/env/spec-default precedence. Added `get_setting_int_positive(db, key, safe_default)` helper that coerces to ≥1 and warns once per key on invalid values.
- **`tools/agent_runner/ticket_pipeline.py`** — Added `claim_intelligence()`, `claim_readiness()`, `record_intake_once()` — all backed by a single atomic UPSERT statement (`INSERT ... ON CONFLICT ... DO UPDATE WHERE`). Extended `maybe_run_readiness_after_intelligence()` to guard its inline chain with `claim_readiness()`.
- **`tools/agent_runner/run_daemon.py`** — Rewrote `poll_github_issues()` to iterate every candidate in one poll, bounded by `MAX_ISSUES_INTAKED_PER_POLL`, tracking `discovered/intaked/skipped_existing/skipped_limit` and emitting the required summary log line. Added lazy singleton `_intel_pool`/`_readiness_pool` (concurrent.futures.ThreadPoolExecutor, sized from settings), `_submit_intelligence/_submit_readiness` with in-flight dedup, and rewrote `poll_ticket_pipeline()` to dispatch to those pools. Pools shut down cleanly in `main()`'s `finally`. `MAX_WORKERS` / dispatcher scheduling is untouched.
- **`docs/daemon-lifecycle.md`** — Documented the four new settings, the summary log format, and the parallel dispatch behavior.
- **`tests/test_daemon_issue_polling.py`** — Updated 3 tests whose old assertions ("only one intake per cycle") no longer hold after the batch-intake change.

### New test files (24 tests, all passing)
- `tests/test_poll_batch_intake.py` — 3 tests: 20-in-one-poll, idempotent repeat, cap+skipped_limit.
- `tests/test_claim_intelligence.py` — 5 tests including 2-thread concurrent claim.
- `tests/test_claim_readiness.py` — 4 tests including 2-thread concurrent claim.
- `tests/test_parallel_bounds.py` — 2 tests verifying pool `max_workers`=4 caps peak concurrency at 4.
- `tests/test_settings_fallback.py` — 6 tests covering `"0"`, `"abc"`, `""`, unset, valid override, and one-warning-per-key.
- `tests/test_execution_workers_unchanged.py` — 4 tests locking in that `MAX_WORKERS` and dispatcher scheduling are byte-untouched.

### Verifications performed
- 24 new T221 tests: all pass.
- All 3 pre-existing `test_ticket_pipeline` failures were confirmed pre-existing (unaffected by my changes).
- 7 environment-dependent failures (real daemon holding singleton lock, dispatcher advisory mode) were confirmed pre-existing.

### Limitations
- I could not run the full pytest suite from top to bottom in this environment because of a stale merge conflict in unrelated daemon-runtime files (`runs/T219/runtime.log`, `apps/dashboard/node_modules/.vite/vitest/results.json`) left over from a background sync; scoped test batches all pass. The conflict is unrelated to T221 and should be resolved by the operator.
- The daemon's auto-commit committed my in-progress changes as commit `4f10774d` before I called for a commit, so no manual commit step remains for T221 itself.
