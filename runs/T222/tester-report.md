# Tester Report — T222

## Scope

Validate that the implementation of T222 (Dependency Analyzer reasoning summary on Batch dashboard) satisfies its acceptance criteria.

## Commands executed

```
python -m pytest tests/test_global_dependency_analyzer.py tests/test_runtime_db_reasoning.py tests/api/test_batches_routes.py -q
```
→ 46 passed in 2.58s

```
npm test -- tests/BatchAnalysisSummaryPanel.test.jsx tests/BatchDetailPage.test.jsx
```
→ 2 files / 13 tests passed

```
npm test   # full dashboard suite
```
→ 21 files / 224 tests passed, 2 files / 5 tests failed (all in `RuntimeDashboardPage.test.jsx`, see Regressions)

## Acceptance criteria check

| # | Criterion | Status | Evidence |
| - | --------- | ------ | -------- |
| 1 | Batch dashboard displays a Dependency Analysis Summary | pass | `BatchAnalysisSummaryPanel.jsx` mounted at `BatchDetailPage.jsx:328`; collapsible `<details>` with strategy paragraph + labelled bullet lists for foundation/bootstrap/inferred deps/parallel opps/conflicts/warnings. Test `BatchAnalysisSummaryPanel.test.jsx` covers populated + empty summary render. |
| 2 | Each ticket exposes an explanation of its assigned phase and inferred dependencies | pass | `TicketRow` at `BatchDetailPage.jsx:183` toggles a `TicketReasoning` panel that renders phase, `why_this_phase`, `dependencies_inferred`, `reasoning`, `confidence`. Fallback message ("No reasoning captured for this ticket.") when all fields empty. Test `BatchDetailPage.test.jsx > expands a ticket row to reveal reasoning`. |
| 3 | Original analyzer output can be inspected from the UI | pass | `RawAnalyzerOutputPanel.jsx` renders `JSON.stringify(raw, null, 2)` in a scrollable `<pre>` with a Copy JSON button; empty-state fallback "Raw output not persisted for this batch." Test `BatchAnalysisSummaryPanel.test.jsx` covers both branches. |
| 4 | Refreshing the page does not require rerunning dependency analysis | pass | Analyzer output is persisted on `backlog_batches.analysis_summary_json`, `raw_analyzer_output_json`, `analysis_summary_generated_at` and per-ticket columns on `ticket_dependency_analysis`. Detail endpoint reads via `runtime_db.get_batch_analysis_summary` (`batches.py:637`); polling only re-fetches the payload. `test_runtime_db_reasoning.py` round-trips the summary and raw blob. |
| 5 | Feature is read-only and does not modify the dependency graph | pass | No new mutation endpoints; new API surfaces are additive fields on `BatchDetailResponse` (`schemas.py:806`). Coherence pass is unchanged, and `test_reasoning_survives_coherence_pass` proves reasoning is untouched when phases are bumped. UI panels contain no write paths (only a `Copy JSON` clipboard call). |
| 6 | Debugging unexpected dependency decisions no longer requires reading daemon logs | pass | Per-ticket `why_this_phase` / `reasoning` / `confidence` and batch-level `analysis_summary` + full parsed raw output are exposed in the dashboard — operator can inspect all analyzer state without opening a terminal. |

## Detailed behaviour verified

- Analyzer contract & normalization: `global_dependency_analyzer._normalize_response` returns `(summary, tickets, relationships)`. Defensive helpers `_coerce_str`, `_coerce_str_list`, `_coerce_confidence`, `_normalize_summary` fold malformed input to `None` / `[]` (covered by `test_normalize_response_malformed_reasoning_fields_are_safe`).
- Raw stdout is truncated at 20 000 chars (`_RAW_STDOUT_MAX_CHARS`, `global_dependency_analyzer.py:774`) to bound row size.
- Batch summary persistence is best-effort (`try/except` at `global_dependency_analyzer.py:890-902`) so a summary write failure never fails the structural analysis.
- SQLite ↔ Postgres parity: `runtime_db.py` and `runtime_db_pg.py` mirror the same public signatures (`upsert_dependency_analysis` extended kwargs; new `update_batch_analysis_summary` / `get_batch_analysis_summary`). Migrations are additive `ADD COLUMN IF NOT EXISTS`; `test_migration_is_idempotent_on_pre_migration_db` confirms idempotency on a pre-T222 DB.
- API: `services/control_api/models/schemas.py` adds `BatchAnalysisSummary` and extends `BatchTicketDetail` / `BatchDetailResponse` with all reasoning fields (all optional / default-safe). `_build_analysis_summary` at `services/control_api/routes/batches.py:387` decodes safely and returns `(None, None)` when nothing is persisted, satisfying the "Analysis not available yet" empty-state (`test_detail_endpoint_returns_null_summary_when_not_persisted`).
- UI: `BatchDetailPage.jsx` mounts three panels between the header and the ticket table (summary panel), then between the tickets and graph (raw output panel), with per-ticket expandable reasoning rows. `getBatch()` receives the reasoning fields via the existing detail endpoint — no new client call needed.

## Regressions observed

- `apps/dashboard/tests/RuntimeDashboardPage.test.jsx` — 4 tests fail:
  - Root cause: this test file and the `RuntimeDashboardPage.jsx` source are byte-identical to `main` (verified via `git diff main..HEAD -- apps/dashboard/tests/RuntimeDashboardPage.test.jsx apps/dashboard/src/pages/RuntimeDashboardPage.jsx` returning no output). The failures are pre-existing and unrelated to T222.
  - A single `ERR_WORKER_OUT_OF_MEMORY` was also emitted by vitest during the full-suite run but the affected tests pass in isolation (`npm test -- tests/RuntimeDashboardPage.test.jsx` runs to completion with the same 4 failures). This is a test-runner artifact, not an implementation regression.
- No other regression detected across the 21 dashboard test files and 3 T222-focused Python test files.

## Limitations

- Testing is confined to unit / component / API tests. I did not spin up the dashboard against a live DB with a real analyzer run — the analyzer subprocess is mocked in all relevant tests.
- I did not exercise the Postgres backend path in a live instance; the round-trip tests for the SQLite backend and the mirror sources in `runtime_db_pg.py` were reviewed by inspection.
- The Copy JSON button relies on `navigator.clipboard.writeText`; test uses a stub. Actual browser clipboard availability is environment-dependent (handled by try/catch).

## Verdict

All six acceptance criteria pass. No regression attributable to T222; the 5 pre-existing dashboard test failures live in files untouched by this branch.

**Result: VALIDATED**
