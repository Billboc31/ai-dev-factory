## Review — T222 (Dependency Analyzer reasoning summary on Batch dashboard)

### Correctness vs. ticket

All four MVP requirements are met:
- **Batch analysis summary** — `BatchAnalysisSummaryPanel.jsx` renders strategy, foundation/bootstrap tickets, inferred dependencies, parallel opportunities, conflicts resolved, warnings.
- **Per-ticket reasoning** — `TicketRow` at `apps/dashboard/src/pages/BatchDetailPage.jsx:183` exposes phase / why / dependencies inferred / reasoning / confidence via an expandable inner row.
- **Raw analyzer output** — `RawAnalyzerOutputPanel.jsx` is collapsible, JSON-formatted, with a Copy JSON button and a truncated-stdout fallback.
- **Persistence** — new columns on `backlog_batches` (`analysis_summary_json`, `raw_analyzer_output_json`, `analysis_summary_generated_at`) and `ticket_dependency_analysis` (`why_this_phase`, `dependencies_inferred_json`, `reasoning`, `confidence`) in both SQLite (`runtime_db.py`) and Postgres (`runtime_db_pg.py`); reasoning is preserved on refresh, no analyzer rerun triggered.

All six acceptance criteria are satisfied by tests: DB round-trip (`test_runtime_db_reasoning.py`), API surfacing (`tests/api/test_batches_routes.py::test_detail_endpoint_surfaces_analysis_summary_and_reasoning`), UI panels (`apps/dashboard/tests/BatchDetailPage.test.jsx`), null-persistence fallback (`test_detail_endpoint_returns_null_summary_when_not_persisted`).

### Scope compliance

Strictly within the ticket. No dependency graph mutation, no phase-computation change, no new endpoints, no write path from the reasoning panels. Coherence-preserves-reasoning is explicitly tested (`test_reasoning_survives_coherence_pass`).

### Code quality & safety

- Defensive normalization: `_coerce_str`, `_coerce_str_list`, `_coerce_confidence`, `_normalize_summary` return safe defaults on any malformed LLM input, exercised by `test_normalize_response_malformed_reasoning_fields_are_safe`. `_normalize_response` is now a 3-tuple return — clean.
- Raw stdout is capped at 20 000 chars (`_RAW_STDOUT_MAX_CHARS`) to bound DB row size; tested.
- Analyzer summary write is best-effort (try/except at `global_dependency_analyzer.py:890-902`) so a summary write failure doesn't fail the structural analysis. Sensible.
- SQLite/Postgres kept in strict lock-step (T208 discipline honored): identical public signatures, mirrored DDL, additive `ADD COLUMN IF NOT EXISTS`, idempotent migration verified against a pre-T222 schema in `test_migration_is_idempotent_on_pre_migration_db`.
- API uses `_safe(runtime_db.get_batch_analysis_summary, …)` so a DB error can't 500 the detail endpoint.
- Frontend `navigator.clipboard.writeText` is wrapped in try/catch for jsdom/blocked environments.

### Minor observations (non-blocking)

- `runtime_db.py::get_batch_analysis_summary` guards `"…" in row.keys()` before indexing the Row; after migration the columns always exist, so the check is redundant but harmless.
- `TicketReasoning` shows a "Phase" line that duplicates the outer row's `Execution phase` column — cosmetic redundancy.
- `<details open={!empty}>` on `BatchAnalysisSummaryPanel` will auto-reopen when the 10 s poll transitions the summary from empty → populated. Consistent with the plan ("default open when summary non-empty") but worth watching for UX regressions.

### No security or scope violations detected

IMPLEMENTATION_APPROVED
