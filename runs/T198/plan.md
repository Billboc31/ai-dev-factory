## Objective

Introduce an advisory Readiness Evaluator that decides whether a ticket can enter the development pipeline. Persist a `ticket_readiness` row per ticket (status `READY_CANDIDATE` / `BLOCKED` with blocking reasons), expose it via API and dashboard, mirroring the existing Ticket Intelligence pattern. Execution behavior is **not** changed.

## Included

- **DB schema (`tools/agent_runner/runtime_db.py`)**
  - Add `CREATE TABLE IF NOT EXISTS ticket_readiness (...)` to `_SCHEMA` with columns: `ticket_id PRIMARY KEY`, `readiness_status` (`not_started|queued|running|ready_candidate|blocked|failed`), `ready_candidate INTEGER`, `blocking_reasons_json TEXT`, `warnings_json TEXT`, `dependency_check_status TEXT`, `approval_check_status TEXT`, `context_freshness_status TEXT`, `human_approval_required INTEGER`, `human_approval_present INTEGER`, `main_sha_when_evaluated TEXT`, `evaluated_at TEXT`, `created_at TEXT NOT NULL`, `updated_at TEXT NOT NULL`.
  - Add `upsert_ticket_readiness(db_path, ticket_id, **fields)` and `get_ticket_readiness(db_path, ticket_id)`, mirroring the `ticket_intelligence` helpers.
  - Rebind both functions in the Postgres backend selection block at the bottom of the file.

- **Postgres backend (`tools/agent_runner/runtime_db_pg.py`)**
  - Add equivalent `ticket_readiness` table creation and `upsert_ticket_readiness` / `get_ticket_readiness` implementations.

- **Evaluator service (`tools/agent_runner/ticket_readiness_evaluator.py`, new)**
  - Public `run_evaluation(db_path, ticket_id, ticket_content, project_root)` callable, designed to run in a background thread; updates `readiness_status` `queued → running → ready_candidate|blocked|failed`; never raises (failures persisted).
  - Internal helpers:
    - `_check_intelligence(db_path, ticket_id)` — fails with `Missing Ticket Intelligence analysis` if `get_ticket_intelligence(...)` returns `None` or `analysis_status != "completed"`.
    - `_check_dependencies(ticket_content, project_root)` — parse `Depends on T\d+`, `After T\d+`, `Blocked by T\d+` (case-insensitive) from the ticket body; for each prerequisite, verify the merge state on `main` (use `git log --grep "T<id>" main` / existing merge metadata helpers in the repo, or check for a closed PR via `runtime_db` if cheaper). Returns `passed|failed` + reasons.
    - `_check_human_approval(intelligence_row, project_root, ticket_id)` — if `requires_human_plan_review == 1`, check for a human-approval marker (e.g. presence of `runs/<ticket>/plan-approved.md` or equivalent existing convention; if no convention exists yet, treat absence as missing and emit `Human plan approval missing`). Returns `passed|failed` + flags `human_approval_required` / `human_approval_present`.
    - `_check_context_freshness(project_root)` — capture `main_sha_when_evaluated` via `git rev-parse main`; set `context_freshness_status="fresh"` (or `unknown` if git fails). No comparison logic in this ticket.
  - Assemble `blocking_reasons`, set `ready_candidate=1` iff every check passes, persist with `evaluated_at=<now>`.

- **API schemas (`services/control_api/models/schemas.py`)**
  - Add `TicketReadiness` (mirrors DB row; lists for `blocking_reasons` / `warnings`) and `TicketReadinessQueued` (`ticket_id`, `readiness_status`).

- **API routes (`services/control_api/routes/readiness.py`, new)**
  - `GET /tickets/{ticket_id}/readiness` → 200 with `TicketReadiness`, 404 if no row.
  - `POST /tickets/{ticket_id}/evaluate-readiness` → 202 with `TicketReadinessQueued`; idempotent on `queued|running`; launches `ticket_readiness_evaluator.run_evaluation` in a daemon thread.
  - Add `/projects/{project_id}/...` variants (same pattern as `intelligence.py`).
  - Register the new router in `services/control_api/main.py` (next to the existing `intelligence` router include).

- **Frontend API helper (`apps/dashboard/src/api/tickets.js`)**
  - Add `getTicketReadiness(ticketId, projectId)` and `postEvaluateReadiness(ticketId, projectId)`.

- **Frontend panel (`apps/dashboard/src/components/TicketReadinessPanel.jsx`, new)**
  - Display: readiness status badge, `READY CANDIDATE` badge when applicable, blocking reasons list, warnings list, last evaluation date, dependency / approval / context-freshness sub-states, an `Evaluate readiness` button that triggers the POST and polls (reuse `usePolling`).
  - Mount the panel on `apps/dashboard/src/pages/TicketDetailPage.jsx` next to `TicketIntelligencePanel`.

- **Tests (under `tests/`)**
  - `test_ticket_readiness_db.py` — schema creation, upsert/get round-trip, JSON-list field handling.
  - `test_ticket_readiness_evaluator.py` — unit tests covering each check in isolation: missing intelligence → blocked; unmerged dependency → blocked with reason; missing human approval → blocked; all-pass → `ready_candidate=True`, `readiness_status="ready_candidate"`.
  - `test_ticket_readiness_api.py` — GET 404 when no row; POST returns 202 + `queued`; idempotency when already `queued|running`; project-scoped route mirror.

## Excluded

- Any change to scheduler, worker dispatch, daemon state machine, or merge logic.
- Implementing the `READY_TO_TAKE` state or any transition out of `READY_CANDIDATE`.
- Comparing `main_sha_when_evaluated` against current `main` to detect staleness (only the field and the `fresh|unknown|stale` enum surface are introduced — `stale` is never produced yet).
- Automatic triggering of readiness evaluation (no daemon hook, no auto-run after ticket intelligence completes). Evaluation runs only on explicit POST.
- Enforcing readiness as a gate before any existing pipeline step.
- Refactors to `ticket_intelligence_analyzer.py` or shared extraction of common helpers between analyzer and evaluator.
- New CLI entry point for the evaluator; it is reachable only via the API in this ticket.

## Acceptance criteria

- `ticket_readiness` table exists in both SQLite and Postgres backends; `upsert_ticket_readiness` / `get_ticket_readiness` round-trip cleanly.
- `POST /tickets/{ticket_id}/evaluate-readiness` returns HTTP 202 with `readiness_status="queued"`, persists a row, and triggers a background evaluation.
- `GET /tickets/{ticket_id}/readiness` returns the persisted result with `blocking_reasons` and `warnings` as JSON arrays.
- Evaluator marks a ticket `BLOCKED` with reason `Missing Ticket Intelligence analysis` when no completed intelligence row exists.
- Evaluator marks a ticket `BLOCKED` with reason `Dependency T<ID> not merged` when any parsed prerequisite is not merged into `main`.
- Evaluator marks a ticket `BLOCKED` with reason `Human plan approval missing` when intelligence has `requires_human_plan_review=1` and no approval marker is present.
- When all checks pass, the row has `readiness_status="ready_candidate"`, `ready_candidate=1`, empty `blocking_reasons`, and a non-null `evaluated_at` + `main_sha_when_evaluated`.
- The dashboard `TicketReadinessPanel` renders the status, badge, reasons, warnings, sub-check states, and last evaluation date, and can trigger evaluation.
- No existing daemon / scheduler / worker code paths are modified; the existing test suite (`pytest tests/`) continues to pass.
