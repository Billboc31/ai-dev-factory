## Objective

Add a hybrid (deterministic + AI) Ticket Intelligence Analyzer that runs before the development cycle, persists structured advisory metadata per ticket in the database, exposes it through two new API endpoints, and displays it on the ticket detail page — without affecting any scheduling or execution behavior.

## Included

### Database

- **`tools/agent_runner/runtime_db.py`** and **`tools/agent_runner/runtime_db_pg.py`**: add `CREATE TABLE IF NOT EXISTS ticket_intelligence` with all fields from the ticket spec (`ticket_id`, `analysis_status`, `difficulty_score`, `difficulty_label`, `risk_score`, `risk_label`, `complexity_factors`, `computed_signals_json`, `recommended_model`, `recommended_model_reason`, `estimated_input_tokens`, `estimated_output_tokens`, `estimated_cost_min`, `estimated_cost_max`, `cost_currency`, `cost_estimate_status`, `queue_rank`, `queue_reason`, `dependency_hints`, `parallel_safe_candidate`, `requires_human_plan_review`, `human_plan_review_reason`, `requires_human_code_review`, `human_code_review_reason`, `autonomous_execution_recommendation`, `analysis_summary`, `created_at`, `updated_at`). One row per ticket (upsert on `ticket_id`). `analysis_status` supports `not_started`, `queued`, `running`, `completed`, `failed`.

### Deterministic Feature Extractor

- **`tools/agent_runner/ticket_intelligence_extractor.py`** (new file): pure-Python module, no AI dependency. Computes and returns a `ComputedSignals` dict from raw ticket text:
  - text length, requirement count, acceptance criteria count
  - presence of risky keywords (`database`, `migration`, `scheduler`, `auth`, `security`, `deployment`, `multi-project`, `worker`, `daemon`)
  - affected domains (`backend`, `frontend`, `database`, `infra`, `orchestration`, `UI`, `tests`) inferred from keyword scan
  - dependency references (`depends on`, `after T\d+`, `requires`, `blocked by`) + count of referenced ticket IDs
  - estimated token size (character count ÷ 4)
  - rough file-impact estimate (count of risky-domain keyword hits)
  - boolean flags: `changes_scheduler`, `likely_needs_db_migration`

### AI Ticket Intelligence Analyzer

- **`tools/agent_runner/ticket_intelligence_analyzer.py`** (new file): orchestrates the hybrid flow:
  1. Calls the extractor to get `computed_signals`
  2. Loads prompt template, injects ticket content + computed signals
  3. Calls the configured AI model via `execute_external_command(exec_cmd, prompt)` from `run_step.py` (provider-agnostic; logical model names from the catalog only — no `anthropic`/`openai` imports)
  4. Uses `subprocess.run(timeout=120)`; on `TimeoutExpired`, persists `analysis_status = failed`
  5. Parses and validates the JSON response against expected field names and types
  6. Normalizes/clamps numeric scores (1–10), fills `cost_estimate_status: "unknown"` when pricing unavailable
  7. Persists result to `ticket_intelligence` via `runtime_db.py`

### Agent Prompt

- **`ai/roles/ticket-intelligence-analyzer.md`** (new file): role definition for the analyzer agent
- **`prompts/ticket-intelligence-analyzer-prompt.md`** (new file): canonical prompt template instructing the model to return the exact JSON schema from the ticket spec; includes placeholder sections for `{{ticket_content}}` and `{{computed_signals}}`

### Model Catalog

- **`tools/agent_runner/model_catalog.py`** (new file): a small configurable dict mapping logical names (`local-qwen`, `cheap-fast-model`, `balanced-code-model`, `advanced-reasoning-model`) to cost-per-token values and provider hints. Read-only at this stage; no routing side-effects.

### API Layer

- **`services/control_api/routes/intelligence.py`** (new file):
  - `GET /api/tickets/{ticket_id}/intelligence` — fetches current analysis row from DB, returns 404 if none exists
  - `POST /api/tickets/{ticket_id}/intelligence/analyze` — validates ticket exists, upserts `analysis_status = queued`, spawns background analysis via `threading.Thread` (same pattern as `run-next` / `resolve-conflicts` in `routes/tickets.py`), returns **202 Accepted** with `{"ticket_id": "...", "analysis_status": "queued"}`
- **`services/control_api/main.py`**: register the new router with prefix `/api/tickets`
- **`services/control_api/models/schemas.py`**: add `TicketIntelligence` Pydantic model matching all DB fields

### Frontend

- **`apps/dashboard/src/components/TicketIntelligencePanel.jsx`** (new file): displays all advisory fields; handles `not_started`, `queued`/`running`, `completed`, and `failed` states with polling; button labels adapt (`Analyze`, `Re-analyze`, `Analysis running`, `Retry analysis`); includes "Advisory only — not used by scheduler yet" badge
- **`apps/dashboard/src/pages/TicketDetailPage.jsx`**: import and render `<TicketIntelligencePanel ticketId={...} />` below the existing timeline section

### Tests

- **`tests/test_ticket_intelligence_extractor.py`** (new): unit tests for all deterministic signals on synthetic ticket strings
- **`tests/test_ticket_intelligence_api.py`** (new): integration tests — 404 when no analysis, POST returns 202 with `queued`, GET after completion, timeout/failure persisted as `failed`
- **`tests/test_ticket_intelligence_db.py`** (new): DB upsert behavior — second insert updates rather than duplicates
- **`apps/dashboard/tests/TicketIntelligencePanel.test.jsx`** (new): Vitest tests for all panel states, advisory badge, and re-analyze/retry behavior

## Excluded

- Changing ticket scheduling, queue ordering, or worker dispatch based on the analysis
- Blocking or auto-routing tickets based on `autonomous_execution_recommendation`
- Implementing parallel execution rules
- Automatically selecting the AI execution model from the analysis output
- Storing historical analysis versions (only the latest record per ticket is kept)
- Provider-specific API integration logic in the model catalog (only logical names and cost hints)
- Admin UI for editing or overriding analysis results

## Acceptance criteria

- `GET /api/tickets/{ticket_id}/intelligence` returns 404 for a ticket with no analysis, and returns all expected fields after an analysis has completed
- `POST /api/tickets/{ticket_id}/intelligence/analyze` returns 202 with `analysis_status: queued` without blocking; background job transitions through `running` → `completed` or `failed`
- AI execution uses `execute_external_command` and logical model names — no provider-specific imports in analyzer code
- Timeout and model failures persist `analysis_status = failed` and are visible in API response and UI
- `computed_signals_json` contains deterministic extractor output (independently verifiable)
- `difficulty_score` and `risk_score` are integers in [1, 10]; `cost_estimate_status` is `"unknown"` when the model is not in the catalog
- Ticket detail page shows the intelligence panel with advisory badge and handles running/failed states without indefinite wait
- Existing ticket states, scheduler loop, and worker dispatch are unmodified (existing test suite still passes)
- `pytest tests/test_ticket_intelligence_*.py` and `vitest apps/dashboard/tests/TicketIntelligencePanel.test.jsx` all pass
