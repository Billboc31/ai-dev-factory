I have enough context. Producing the plan artifact now.

## Objective

Expose the Global Dependency Analyzer's reasoning in the Batch dashboard so every phase assignment and inferred dependency is explainable, without rerunning analysis on refresh. Extend the analyzer prompt/schema, persist the new fields, surface them through the Batch API, and render three new UI blocks (batch analysis summary, per-ticket reasoning, raw analyzer output).

## Included

### 1. Extend the analyzer output schema (LLM contract)

- `tools/agent_runner/global_dependency_analyzer.py` (`_INLINE_PROMPT`, lines 83–152) and the mirrored `prompts/global-dependency-analyzer-prompt.md`: extend the required JSON with
  - top-level `analysis_summary` object:
    - `strategy` (string) — one-paragraph overall implementation strategy
    - `foundation_tickets` (list[str])
    - `bootstrap_tickets` (list[str])
    - `important_inferred_dependencies` (list[str] — human-readable bullets)
    - `parallel_opportunities` (list[str])
    - `conflicts_resolved` (list[str])
    - `warnings` (list[str])
  - each element of `tickets[]` gains
    - `why_this_phase` (string, 1–3 sentences)
    - `dependencies_inferred` (list[str] — short justifications, one per depended-on ticket)
    - `reasoning` (string, free-form)
    - `confidence` (string, one of `low` | `medium` | `high`, optional)
- Update the JSON schema example block, the "Output invariants" wording, and the `type` enum sentence — keep required invariants unchanged.
- Extend `_normalize_response()` (line 274) to coerce the new fields defensively:
  - `_coerce_str()` helper (trim, `None` on empty).
  - `_coerce_confidence()` restricted to `{"low","medium","high"}` else `None`.
  - Missing/malformed fields become `None`/`[]` — analyzer must never crash on partial JSON.
- Return the summary alongside tickets from a small internal container (e.g. new `NormalizedAnalysis` dataclass or `_normalize_response` returns a 3-tuple `(summary, tickets, relationships)`).

### 2. Capture the raw analyzer output

- In `run_global_analysis()` (line 661), keep `stdout` (the pre-parse text) and `raw` (parsed dict) so both can be persisted. Store as a single `raw_analyzer_output` JSON string containing at least `{"stdout_excerpt": str[:20000], "parsed": raw}`. Truncate stdout to 20 000 chars to bound DB size.

### 3. Persistence — schema + upserts (SQLite + Postgres in lock-step)

Batch-level fields (one row per batch) live on `backlog_batches`; per-ticket fields live on `ticket_dependency_analysis`.

- `tools/agent_runner/runtime_db.py`:
  - `_SCHEMA` (line 224): add columns to `ticket_dependency_analysis` — `why_this_phase TEXT`, `dependencies_inferred_json TEXT`, `reasoning TEXT`, `confidence TEXT`.
  - Add columns to `backlog_batches` schema — `analysis_summary_json TEXT`, `raw_analyzer_output_json TEXT`, `analysis_summary_generated_at TEXT`.
  - Add two idempotent migration helpers mirroring `_ensure_backlog_batches_columns` / `_ensure_ticket_intelligence_lifecycle_columns`:
    - `_TICKET_DEPENDENCY_ANALYSIS_COLUMNS` tuple + `_ensure_ticket_dependency_analysis_columns(conn)`.
    - Extend `_BACKLOG_BATCHES_COLUMNS` with the three new columns.
  - Wire both helpers into `init_runtime_db` (where the other `_ensure_*` helpers are called).
  - Extend `upsert_dependency_analysis()` (line 1343) with kwargs `why_this_phase`, `dependencies_inferred`, `reasoning`, `confidence`; update INSERT + ON CONFLICT UPDATE SET.
  - Extend `get_dependency_analysis()` (line 1391) to decode `dependencies_inferred_json` → `dependencies_inferred`.
  - Add two new helpers next to backlog batch functions:
    - `update_batch_analysis_summary(db_path, batch_id, *, analysis_summary, raw_analyzer_output, generated_at)` — writes the two JSON columns + timestamp on `backlog_batches`.
    - `get_batch_analysis_summary(db_path, batch_id) -> dict | None` — returns `{"analysis_summary": …, "raw_analyzer_output": …, "generated_at": …}` with JSON decoded, `None` when the batch has no analysis persisted.
- `tools/agent_runner/runtime_db_pg.py`: mirror **all** of the above — DDL in `_DDL` (line 279), migration SQL in the Postgres migration block (see the `_TICKET_INTELLIGENCE_LIFECYCLE_MIGRATION` at line 299 as template), and matching `upsert_dependency_analysis`/`get_dependency_analysis`/`update_batch_analysis_summary`/`get_batch_analysis_summary` implementations. Keep the SQLite/Postgres public signatures identical (T208 discipline).

### 4. Wire persistence into the analyzer run

- In `_persist()` (line 630) of `global_dependency_analyzer.py`, forward the new per-ticket fields to `upsert_dependency_analysis`.
- In `run_global_analysis()`, after coherence, call `runtime_db.update_batch_analysis_summary(...)` with the analyzer's `analysis_summary` dict and the truncated raw output blob.
- If the LLM omits `analysis_summary` entirely, persist an empty summary dict (`{}`) and still store the raw output, so the UI can render the raw section for debugging even when the structured summary is missing.

### 5. API — surface reasoning through the Batch endpoints

- `services/control_api/models/schemas.py`:
  - New model `BatchAnalysisSummary` with fields matching §1 (`strategy`, `foundation_tickets: list[str]`, `bootstrap_tickets: list[str]`, `important_inferred_dependencies: list[str]`, `parallel_opportunities: list[str]`, `conflicts_resolved: list[str]`, `warnings: list[str]`, `generated_at: str | None`).
  - Extend `BatchTicketDetail` (line 770) with `why_this_phase: str | None`, `dependencies_inferred: list[str] = []`, `reasoning: str | None`, `confidence: str | None`.
  - Extend `BatchDetailResponse` (line 783) with `analysis_summary: BatchAnalysisSummary | None = None` and `raw_analyzer_output: dict | None = None`.
- `services/control_api/routes/batches.py`:
  - `_build_ticket_details()` (line 319): read the new keys from the per-ticket analysis row and populate the new fields.
  - `_detail_payload()` (line 578): call `runtime_db.get_batch_analysis_summary(db_path, batch_id)` (via `_safe`) and populate `analysis_summary` + `raw_analyzer_output` on the response.
  - No new endpoint — everything ships through the existing `GET /dispatcher/batches/{batch_id}` (global + project-scoped variants both benefit because they share `_detail_payload`).

### 6. UI — three new sections on the Batch detail page

- `apps/dashboard/src/pages/BatchDetailPage.jsx`: add three sections between the header and the tickets table (only the tickets section wires new columns).
  - `<BatchAnalysisSummaryPanel summary={detail.analysis_summary} generatedAt={…} />` — new component in `apps/dashboard/src/components/BatchAnalysisSummaryPanel.jsx`.
    - Collapsible `<details>` titled "Dependency Analysis Summary" (default open when `summary` non-empty, else collapsed).
    - Renders `strategy` as a paragraph, then labelled bullet lists for `foundation_tickets`, `bootstrap_tickets`, `important_inferred_dependencies`, `parallel_opportunities`, `conflicts_resolved`, `warnings`. Skip empty groups.
    - Shows a muted "Analysis not available yet" fallback when `summary` is `null` / all fields empty.
  - Extend `TicketsTable` (line 108) so each row is expandable (React `useState` per ticket id, or a nested `<details>` inside a wide-spanning `<td colspan>`). Expanded content renders:
    - Phase (`ticket.execution_phase`)
    - "Why this phase?" (`ticket.why_this_phase`)
    - "Dependencies inferred" — bullet list of `ticket.dependencies_inferred`
    - "Reasoning" (`ticket.reasoning`)
    - "Confidence" badge (`ticket.confidence`) with a small pill class.
    - When all four are `null`/empty, show "No reasoning captured for this ticket."
  - `<RawAnalyzerOutputPanel raw={detail.raw_analyzer_output} />` — new component in `apps/dashboard/src/components/RawAnalyzerOutputPanel.jsx`.
    - Collapsible `<details>` titled "Raw Dependency Analyzer Output" (closed by default).
    - Renders `JSON.stringify(raw, null, 2)` inside a scrolling `<pre>`. Includes a "Copy JSON" button using `navigator.clipboard.writeText`.
    - Shows "Raw output not persisted for this batch" when `raw` is null.
- `apps/dashboard/src/api/batches.js`: no signature change — `getBatch()` already returns the full detail payload.
- Read-only guarantee: none of the three sections mutate state; polling (`fetchAll` at line 181) already refreshes them.

### 7. Tests

- `tests/test_global_dependency_analyzer.py`: add cases that
  - Parse a mocked LLM response containing `analysis_summary` + per-ticket reasoning fields and confirm `_normalize_response` extracts them.
  - Confirm normalization coerces missing/malformed reasoning fields to safe defaults (never raises).
  - Confirm the coherence pass leaves reasoning fields untouched even when phases are bumped.
  - Confirm `run_global_analysis` invokes `runtime_db.update_batch_analysis_summary` with the parsed summary and a truncated raw output payload (patch subprocess + DB helpers).
- `tests/test_runtime_db_pg.py` + a new/extended sqlite test file: assert
  - migrations add the four new `ticket_dependency_analysis` columns and the three new `backlog_batches` columns idempotently on pre-existing databases (build a DB with the pre-migration schema, run `init_runtime_db`, verify `PRAGMA table_info` / `information_schema.columns`).
  - `upsert_dependency_analysis` / `get_dependency_analysis` round-trip the new fields.
  - `update_batch_analysis_summary` + `get_batch_analysis_summary` round-trip a full summary dict and the raw output blob.
- Extend the existing control-api test for `GET /dispatcher/batches/{batch_id}` (search under `tests/` for `test_batch*` or `test_control_api*`) to assert `analysis_summary`, `raw_analyzer_output`, and the per-ticket reasoning fields are surfaced.
- `apps/dashboard/tests/` (or the equivalent test root already used by T219 dashboard tests): add a component test rendering `BatchAnalysisSummaryPanel` with populated and empty summaries; confirm the raw output panel toggles.

### 8. Backwards compatibility

- Every new field is optional in the schema and defaults to `None` / `[]`.
- Batches analyzed before this ticket keep working: they simply render "Analysis not available yet" / "Raw output not persisted" in the UI until the next dependency analysis run refreshes them. The existing `recompute-dependencies` operator action already lets users trigger a rerun to populate the new fields.

## Excluded

- Changing the shape of the existing dependency graph (nodes, edges, phase computation) — the feature is read-only.
- Changing conflict-resolution or phase-bumping logic in `_enforce_coherence`.
- Editing dependencies from the UI, overriding phases, or any write path from the reasoning panels.
- Streaming intermediate analyzer reasoning tokens or a "re-run analysis" button (a `recompute-dependencies` action already exists and is out of scope to change).
- Localization / translation of reasoning strings (rendered verbatim as returned by the LLM).
- Per-ticket historical timeline of past analyses — we overwrite the row via UPSERT as today.
- Adding a new REST endpoint — reasoning ships through the existing batch-detail payload.
- Postgres migration for existing production databases: rely on the additive `ADD COLUMN IF NOT EXISTS` pattern already used elsewhere; no data backfill script.

## Acceptance criteria

- Running the analyzer against a batch persists a non-null `backlog_batches.analysis_summary_json` and `raw_analyzer_output_json`, and per-ticket `why_this_phase` / `dependencies_inferred_json` / `reasoning` (verifiable via `sqlite3` or `psql`).
- `GET /dispatcher/batches/{batch_id}` (both global and project-scoped) returns `analysis_summary` (non-null when persisted), `raw_analyzer_output` (non-null when persisted), and per-ticket `why_this_phase` / `dependencies_inferred` / `reasoning` / `confidence` fields for every ticket that has an analysis row.
- On `/dispatcher/batches/{batch_id}` (and the project-scoped variant), the Batch dashboard renders three new UI elements: a collapsible "Dependency Analysis Summary" section, per-ticket expandable reasoning rows, and a collapsible "Raw Dependency Analyzer Output" section.
- Refreshing the dashboard (browser reload or 10-s polling tick) does not trigger a rerun of dependency analysis — inspecting `dependency_analysis_attempts` and `backlog_batches.analysis_summary_generated_at` shows no change across refreshes.
- Batches without persisted reasoning (pre-migration or analysis-failed batches) load the dashboard without errors, and the summary/raw panels show explicit fallbacks ("Analysis not available yet", "Raw output not persisted for this batch").
- All existing tests still pass; new unit tests cover normalization defaults, DB round-trip of the new fields, and the API surfaces the new fields.
- Idempotent migrations: running `init_runtime_db` twice against a DB that already has the new columns is a no-op (no duplicate-column errors).
- No mutation endpoints are added; the feature is strictly read-only from the UI's perspective.
