Now I have enough context to produce the plan.

## Objective

Add a hybrid (deterministic + AI) Ticket Intelligence Analyzer that runs before the development cycle, persists structured advisory metadata per ticket in the database, exposes it through two new API endpoints, and displays it on the ticket detail page — without affecting any scheduling or execution behavior.

## Included

### Database

- **`tools/agent_runner/runtime_db.py`**: add `CREATE TABLE IF NOT EXISTS ticket_intelligence` with all fields from the ticket spec (`ticket_id`, `analysis_status`, `difficulty_score`, `difficulty_label`, `risk_score`, `risk_label`, `complexity_factors`, `computed_signals_json`, `recommended_model`, `recommended_model_reason`, `estimated_input_tokens`, `estimated_output_tokens`, `estimated_cost_min`, `estimated_cost_max`, `cost_currency`, `cost_estimate_status`, `queue_rank`, `queue_reason`, `dependency_hints`, `parallel_safe_candidate`, `requires_human_plan_review`, `human_plan_review_reason`, `requires_human_code_review`, `human_code_review_reason`, `autonomous_execution_recommendation`, `analysis_summary`, `created_at`, `updated_at`). One row per ticket (upsert on `ticket_id`).

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
  3. Calls the configured AI model (via existing Claude API integration pattern in the project)
  4. Parses and validates the JSON response against expected field names and types
  5. Normalizes/clamps numeric scores (1–10), fills `cost_estimate_status: "unknown"` when pricing unavailable
  6. Persists result to `ticket_intelligence` via `runtime_db.py`

### Agent Prompt

- **`ai/roles/ticket-intelligence-analyzer.md`** (new file): role definition for the analyzer agent
- **`prompts/ticket-intelligence-analyzer-prompt.md`** (new file): canonical prompt template instructing the model to return the exact JSON schema from the ticket spec; includes placeholder sections for `{{ticket_content}}` and `{{computed_signals}}`

### Model Catalog

- **`tools/agent_runner/model_catalog.py`** (new file): a small configurable dict mapping logical names (`local-qwen`, `cheap-fast-model`, `balanced-code-model`, `advanced-reasoning-model`) to cost-per-token values and provider hints. Read-only at this stage; no routing side-effects.

### API Layer

- **`services/control_api/routes/intelligence.py`** (new file):
  - `GET /api/tickets/{ticket_id}/intelligence` — fetches current analysis row from DB, returns 404 if none exists
  - `POST /api/tickets/{ticket_id}/intelligence/analyze` — triggers the analyzer synchronously, persists result, returns it
- **`services/control_api/main.py`**: register the new router with prefix `/api/tickets`
- **`services/control_api/models/schemas.py`**: add `TicketIntelligence` Pydantic model matching all DB fields

### Frontend

- **`apps/dashboard/src/components/TicketIntelligencePanel.jsx`** (new file): displays all advisory fields in a card/section; includes "Advisory only — not used by scheduler yet" badge; shows a "Re-analyze" button that calls `POST /api/tickets/:id/intelligence/analyze`; handles loading and error states
- **`apps/dashboard/src/pages/TicketDetailPage.jsx`**: import and render `<TicketIntelligencePanel ticketId={...} />` below the existing timeline section

### Tests

- **`tests/test_ticket_intelligence_extractor.py`** (new): unit tests for all deterministic signals on synthetic ticket strings; covers keyword detection, dependency hint parsing, token estimation
- **`tests/test_ticket_intelligence_api.py`** (new): integration tests for both API endpoints — 404 when no analysis exists, happy-path GET after POST, re-run updates `updated_at`
- **`tests/test_ticket_intelligence_db.py`** (new): tests DB upsert behavior — second insert updates rather than duplicates
- **`apps/dashboard/tests/TicketIntelligencePanel.test.jsx`** (new): Vitest tests for panel rendering with mock data, advisory badge presence, re-analyze button behavior

## Excluded

- Changing ticket scheduling, queue ordering, or worker dispatch based on the analysis
- Blocking or auto-routing tickets based on `autonomous_execution_recommendation`
- Implementing parallel execution rules
- Automatically selecting the AI execution model from the analysis output
- Storing historical analysis versions (only the latest record per ticket is kept)
- Provider-specific API integration logic in the model catalog (only logical names and cost hints)
- Admin UI for editing or overriding analysis results

## Acceptance criteria

- `GET /api/tickets/{ticket_id}/intelligence` returns 404 for a ticket with no analysis, and returns all expected fields after an analysis has been run
- `POST /api/tickets/{ticket_id}/intelligence/analyze` runs the hybrid analyzer and persists the result; a second call updates `updated_at` without creating a duplicate row
- `computed_signals_json` in the DB contains the output of the deterministic extractor (independently verifiable)
- `difficulty_score` and `risk_score` are integers in [1, 10]; `cost_estimate_status` is `"unknown"` when the model is not in the catalog
- The ticket detail page displays the "Ticket Intelligence" section with all advisory fields and the "Advisory only — not used by scheduler yet" badge
- The "Re-analyze" button triggers `POST` and refreshes the panel without a full page reload
- Existing ticket states, the scheduler loop, and the worker dispatch logic are unmodified (confirmed by existing test suite passing)
- `pytest tests/test_ticket_intelligence_*.py` and `vitest apps/dashboard/tests/TicketIntelligencePanel.test.jsx` all pass
