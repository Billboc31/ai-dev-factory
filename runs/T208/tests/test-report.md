Test report written to `runs/T208/tests/test-report.md`.

**Result:** APPROVED.

- **Tests:** 53 passed / 1 failed on the targeted suite. The single failure (`test_default_backend_is_sqlite`) is pre-existing on `main` — reproduced after reverting all T208-touched files.
- **All 9 acceptance criteria:** PASS. Background reliability is enforced by three layers (inner `except`, top-level `finally`-guard, `_bg` wrapper) so no row can stay in `queued`/`running`. AI calls have an enforced wall-clock timeout via `Popen`+`communicate(timeout)`+`kill` (env-tunable `_ANALYSIS_TIMEOUT`, default 120s). New schema columns (`started_at`, `completed_at`, `failed_at`, `failure_origin`) are persisted on every path, migrated idempotently on both SQLite and Postgres, surfaced through the API model and rendered in the dashboard. Lifecycle log lines (`intel.queued`/`started`/`step.*`/`ai_request.*`/`persisted`/`reaped`) are emitted in the mandated order. The reaper now preserves the prior failure summary.
- **Regressions:** none.
- **Blocking issues:** none.
- **Non-blocking caveats** documented in the report: the reaper overwrites the prior `failure_origin` field with `"reaper-confirmed"` (preserves the summary text, which is what the AC requires); Postgres lifecycle assertions use DDL/migration-string fallback (explicitly allowed by plan §9).
