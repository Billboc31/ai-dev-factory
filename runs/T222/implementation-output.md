Implementation complete. Summary:

## Changes

### Analyzer contract & persistence
- `tools/agent_runner/global_dependency_analyzer.py`: extended `_INLINE_PROMPT` and matched `prompts/global-dependency-analyzer-prompt.md` with the new `analysis_summary` + per-ticket reasoning fields (`why_this_phase`, `dependencies_inferred`, `reasoning`, `confidence`). `_normalize_response` now returns a 3-tuple `(summary, tickets, relationships)` and coerces missing/malformed fields to safe defaults. `run_global_analysis` persists the summary and a truncated (`≤20000` chars) raw analyzer output.

### DB layer (SQLite + Postgres kept in lock-step)
- `runtime_db.py`: added 3 columns to `backlog_batches`, 4 columns to `ticket_dependency_analysis`, idempotent migration helpers, extended `upsert_dependency_analysis`, decoded the new list in `get_dependency_analysis`, added `update_batch_analysis_summary` / `get_batch_analysis_summary`.
- `runtime_db_pg.py`: mirrored DDL + `_T222_REASONING_MIGRATION` (additive `ADD COLUMN IF NOT EXISTS`) + same signatures for the new helpers.

### API
- `services/control_api/models/schemas.py`: added `BatchAnalysisSummary`, extended `BatchTicketDetail` and `BatchDetailResponse`.
- `services/control_api/routes/batches.py`: `_build_ticket_details` fills the new per-ticket reasoning fields; `_detail_payload` now attaches `analysis_summary` and `raw_analyzer_output` via a new `_build_analysis_summary` helper. No new endpoints.

### UI
- New `BatchAnalysisSummaryPanel.jsx` (collapsible, empty-state fallback).
- New `RawAnalyzerOutputPanel.jsx` (collapsible, JSON block, Copy JSON button).
- `BatchDetailPage.jsx`: mounted both panels, made each ticket row expandable with a `TicketReasoning` block (phase / why / dependencies inferred / reasoning / confidence pill).

### Tests
- `tests/test_global_dependency_analyzer.py`: 8 new cases covering normalization defaults, malformed-input safety, DB round-trip, coherence-preserves-reasoning, missing summary → raw still persists, stdout truncation.
- `tests/test_runtime_db_reasoning.py` (new): schema migrations idempotent on pre-migration DBs, upsert/get round-trip for reasoning fields, summary + raw round-trip.
- `tests/api/test_batches_routes.py`: added `get_batch_analysis_summary` to the SQLite reinjection, new tests asserting reasoning and summary surface through `/dispatcher/batches/{id}`.
- `apps/dashboard/tests/BatchAnalysisSummaryPanel.test.jsx` (new): component tests for populated/empty summaries and the raw-output panel (Copy JSON).
- `apps/dashboard/tests/BatchDetailPage.test.jsx`: extended fixture with reasoning/summary, tests for panel render + row expansion.

### Results
- Python: 46 T222-related tests pass (analyzer 20, DB reasoning 7, API 19).
- JS: 13/13 targeted dashboard tests pass. Pre-existing `RuntimeDashboardPage.test.jsx` failures are unrelated (they were already failing on the untouched `main`-tracked code, verified by stashing and re-running).
