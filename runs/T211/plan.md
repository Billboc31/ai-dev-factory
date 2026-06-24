I have enough context. Now I produce the plan artifact.

## Objective

Introduce a server-side `TicketExecutionEligibilityService` that aggregates the existing Intelligence, Readiness, Rules, Approval and dependency state into a single read-only `READY_TO_TAKE` decision per ticket, exposes it via a new API endpoint, and surfaces it in the workflow timeline UI introduced in T209. No existing decision logic, scheduler, or worker behaviour changes.

## Included

- `tools/agent_runner/ticket_execution_eligibility.py` (new module):
  - `evaluate_eligibility(db_path, project_root, ticket_id, *, ticket_content=None, project_id=None) -> dict` — pure aggregator. Reads existing artefacts only; never writes to the DB.
  - Loads: `runtime_db.get_ticket_intelligence`, `runtime_db.get_ticket_readiness`, `runtime_db.get_ticket_rule_evaluation`, `runtime_db.get_latest_ticket_approval(..., "execution")` and `..., "plan")`, and ticket runtime `state.json`.
  - Reuses `ticket_readiness_evaluator._extract_dependencies` + `ticket_merge_state.is_ticket_merged` for the dependency check (import only — no copy of the logic).
  - Evaluates checks in a fixed order (`intelligence` → `dependencies` → `readiness` → `rules` → `approval`) and returns the first failing one in `blocking_step`.
  - Output schema (single source of truth, also the API response body):
    ```json
    {
      "ticket_id": "T211",
      "ready_to_take": false,
      "status": "BLOCKED" | "READY_TO_TAKE" | "WAITING_HUMAN_ACTION" | "DEPENDENCY_BLOCKED" | "UNKNOWN",
      "reason": "Human plan approval required",
      "next_action": "Approve plan review",
      "blocking_step": "intelligence" | "dependencies" | "readiness" | "rules" | "approval" | null,
      "checks": {
        "intelligence":  {"status": "passed|pending|failed|unknown", "detail": "..."},
        "dependencies":  {"status": "passed|pending|failed|unknown", "detail": "...", "unmet": ["T001"]},
        "readiness":     {"status": "passed|pending|failed|unknown", "detail": "..."},
        "rules":         {"status": "passed|pending|failed|unknown", "detail": "..."},
        "approval":      {"status": "passed|pending|failed|unknown", "detail": "..."}
      },
      "evaluated_at": "2026-06-24T…Z"
    }
    ```
  - `status` mapping (deterministic):
    - all checks `passed` ⇒ `READY_TO_TAKE`, `ready_to_take=true`.
    - first failing check is `dependencies` ⇒ `DEPENDENCY_BLOCKED`.
    - first failing check is `approval` (intelligence requested human plan review and it is not present) ⇒ `WAITING_HUMAN_ACTION`.
    - any other failing check (intelligence/readiness/rules) ⇒ `BLOCKED`.
    - data missing for every check ⇒ `UNKNOWN`.

- `services/control_api/models/schemas.py`:
  - Add `TicketExecutionEligibilityCheck`, `TicketExecutionEligibility` Pydantic models matching the dict above.

- `services/control_api/routes/eligibility.py` (new):
  - `GET /tickets/{ticket_id}/eligibility` and project-scoped `GET /projects/{project_id}/tickets/{ticket_id}/eligibility`.
  - Reuses the request helpers from existing routes (`_root`, `_db_path`, `_worktrees_dir`) and `artifact_reader.get_ticket` for 404s.
  - Reads `ticket.md` via `runtime_resolver.resolve_ticket_run_dir` to feed dependency extraction (same pattern as `readiness.py`).
  - Calls `ticket_execution_eligibility.evaluate_eligibility(...)` synchronously (no background thread, no DB writes).

- `services/control_api/main.py`:
  - Import and mount `eligibility.router` and `eligibility.project_router` next to the existing readiness/rules mounts.

- `apps/dashboard/src/api/tickets.js`:
  - Add `getTicketEligibility(id, projectId)` calling the new endpoint.

- `apps/dashboard/src/pages/TicketDetailPage.jsx`:
  - Fetch eligibility alongside the existing workflow data and pass it to `TicketWorkflowTimeline` as a new `eligibility` prop (and into the `readyToTake` step content).
  - When the eligibility payload is available, drive `globalSummary` and the `readyToTake` step from the server payload (mapping `status` → existing badge labels: `READY TO TAKE`, `BLOCKED`, `WAITING HUMAN ACTION`, `DEPENDENCY BLOCKED`). Fall back to the current client-side derivation when the payload is missing/loading so the page never goes blank.

- `apps/dashboard/src/components/TicketWorkflowTimeline.jsx`:
  - Add `WAITING HUMAN ACTION` and `DEPENDENCY BLOCKED` entries to `GLOBAL_STATUS_STYLES`.
  - Accept an optional `eligibility` prop; render its `reason` / `next_action` in `GlobalSummary` when present (no change when absent).

- `apps/dashboard/src/lib/ticketWorkflowStatus.js`:
  - Add `eligibilityToGlobalSummary(eligibility)` helper. Existing `deriveStepStatuses` / `deriveGlobalSummary` remain untouched as the offline fallback.

- Tests:
  - `tests/test_ticket_execution_eligibility.py`: unit tests for the aggregator covering each of the documented example decisions (all-green ⇒ `READY_TO_TAKE`; plan approval missing ⇒ `WAITING_HUMAN_ACTION`; dep `T001` not merged ⇒ `DEPENDENCY_BLOCKED`; intelligence missing ⇒ `BLOCKED` with `blocking_step="intelligence"`; rules blocked ⇒ `BLOCKED` with `blocking_step="rules"`; nothing computed yet ⇒ `UNKNOWN`).
  - `tests/test_ticket_eligibility_api.py`: FastAPI client tests for the GET routes (200 happy path, 404 unknown ticket, payload shape).
  - `tests/test_execution_rules_pipeline_untouched.py` style assertion: an `import`-level snapshot test verifying the existing `ticket_readiness_evaluator`, `execution_rules_engine`, `ticket_intelligence_analyzer`, and `ticket_approval_service` modules are not modified by this ticket (file SHA fixed in test, or simply: no production code outside the new module/routes/UI files changes).
  - Dashboard test: extend or add to `apps/dashboard/src/lib/__tests__/ticketWorkflowStatus.test.js` (if present, otherwise create) to cover the new status labels in the timeline; add a snapshot for `TicketWorkflowTimeline` with `status="DEPENDENCY BLOCKED"`.

## Excluded

- No automatic worker assignment, scheduler integration, or dispatcher.
- No changes to `ticket_readiness_evaluator`, `execution_rules_engine`, `ticket_intelligence_analyzer`, `ticket_approval_service`, or any of their tables/columns.
- No persistence of the eligibility result (the service is read-only; no new SQLite table, no upsert).
- No POST/PUT endpoints (no `evaluate-eligibility`); the GET endpoint recomputes on demand from already-persisted upstream rows.
- No changes to `runs/<ticket>/state.json` semantics or to the existing `ready_to_take` value emitted by `ticket_readiness_evaluator` (kept for backward compatibility; the new service is additive).
- No new permissions, no auth changes, no migration.
- No backport of the client-side derivation removal: `deriveStepStatuses`/`deriveGlobalSummary` remain as the loading/offline fallback and are not deleted.

## Acceptance criteria

- `tools/agent_runner/ticket_execution_eligibility.py` exists and exports `evaluate_eligibility`.
- `GET /tickets/{ticket_id}/eligibility` and `GET /projects/{project_id}/tickets/{ticket_id}/eligibility` return a JSON body matching the `TicketExecutionEligibility` schema, with the documented `status` / `reason` / `next_action` / `blocking_step` fields.
- For each documented scenario in the ticket (all-green, plan approval pending, dependency `T001` not merged) the new endpoint returns the expected `status` and `blocking_step`.
- `git diff main -- tools/agent_runner/ticket_readiness_evaluator.py tools/agent_runner/execution_rules_engine.py tools/agent_runner/ticket_intelligence_analyzer.py tools/agent_runner/ticket_approval_service.py` is empty.
- No new column, table, or migration is added to `runtime_db`.
- The Ticket detail page displays the eligibility status badge (one of `READY TO TAKE`, `BLOCKED`, `WAITING HUMAN ACTION`, `DEPENDENCY BLOCKED`) in the workflow timeline global summary, with its reason and next action, sourced from the new endpoint.
- The dashboard still renders the timeline when the eligibility endpoint is loading or returns 404 (fallback to existing client-side derivation).
- `pytest tests/test_ticket_execution_eligibility.py tests/test_ticket_eligibility_api.py` passes.
- The full existing test suite (`pytest`) and the dashboard test suite continue to pass without modification to unrelated tests.
- No scheduler/worker/daemon code path is invoked by the new endpoint (verified by absence of imports of `run_ticket`, `run_daemon`, or supervisor modules from `ticket_execution_eligibility.py` and `routes/eligibility.py`).
