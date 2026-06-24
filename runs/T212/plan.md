## Objective
Introduce a read-only advisory `TicketDispatcherService` that recommends the next ticket(s) to execute based on `READY_TO_TAKE` eligibility, intelligence score, queue order, and ticket age, plus a dedicated Dashboard page exposing the recommendations. The dispatcher is fully opt-in via a `mode` setting (`off` by default) so the existing ticket execution chain behaves exactly as it does today when the dispatcher is not enabled.

## Included

### Backend — dispatcher mode configuration
- `tools/agent_runner/ticket_dispatcher.py` (new):
  - `DISPATCHER_MODES = ("off", "advisory", "manual", "auto")` (constant).
  - `get_dispatcher_mode() -> str` — reads `AI_DEV_FACTORY_DISPATCHER_MODE` env var, defaults to `"off"`, validates against `DISPATCHER_MODES`, treats `"auto"` as not-yet-implemented (returns `"auto"` but recommendation logic refuses to act on it for now; this ticket is scoped to `off`/`advisory`/`manual`).

### Backend — service
- `tools/agent_runner/ticket_dispatcher.py` (same file):
  - Pure-read function:
    ```python
    def get_recommended_tickets(
        db_path,
        project_root: Path,
        *,
        project_id: str | None = None,
        mode: str | None = None,
        limit: int | None = None,
    ) -> dict
    ```
  - Behavior:
    - If `mode` resolves to `"off"`: return `{"mode": "off", "recommendations": [], "blocked": [], "evaluated_at": <iso>}` and perform no further evaluation work.
    - Otherwise:
      1. Enumerate open tickets from `runtime_db.list_ticket_runtime(db_path)` (filter out states already excluded by `FORBIDDEN_RUNNER_STATES` / archived / `pr_ready` / `done` per `board_service`).
      2. For each ticket, call `ticket_execution_eligibility.evaluate_eligibility(...)` to obtain the aggregated decision (pure read — no writes).
      3. Fetch `ticket_intelligence` row (for `difficulty_score`, `queue_rank`, `difficulty_label`).
      4. Compute a deterministic `score` (0–100) combining:
         - `+50` baseline if `ready_to_take=True`, else `0`;
         - intelligence bonus (lower `queue_rank` → higher bonus, e.g. `max(0, 30 - queue_rank)` when `queue_rank` is set);
         - difficulty bonus (`trivial`/`simple` favored slightly);
         - age bonus from `updated_at` (older eligible tickets get a small uplift, capped).
      5. Rank READY_TO_TAKE tickets by descending score (stable tiebreak: lower `queue_rank`, then older `updated_at`, then `ticket_id`).
      6. Build `recommendations` for ready tickets and `blocked` for not-ready tickets (with `blocking_step` and `reason` from the eligibility payload).
  - Returned shape:
    ```python
    {
      "mode": "advisory" | "manual" | "off" | "auto",
      "project_id": str | None,
      "evaluated_at": "<iso8601>",
      "recommendations": [
        {"ticket_id", "rank", "score", "ready_to_take": True,
         "intelligence": {"difficulty_score", "difficulty_label", "queue_rank"},
         "reason": "READY_TO_TAKE, high priority, no blockers"}
      ],
      "blocked": [
        {"ticket_id", "ready_to_take": False, "status", "blocking_step", "reason"}
      ],
    }
    ```
  - The service never writes to the DB, never mutates `state.json`, never starts a ticket, and never calls into the daemon/runner — it only reads and computes.

### Backend — API routes
- `services/control_api/routes/dispatcher.py` (new), mirroring the style of `routes/eligibility.py`:
  - `GET /dispatcher/status` → `{ "mode": "...", "available_modes": [...], "auto_enabled": False }`.
  - `GET /dispatcher/recommendations` (project-agnostic) and `GET /projects/{project_id}/dispatcher/recommendations` → wraps `get_recommended_tickets(...)`. Honors `?mode=` override only for `advisory`; `off` always returns empty payload; `auto` returns `not_implemented` field set to `True`.
  - When `mode == "off"` the endpoint still responds 200 with the empty payload (so the UI can show "dispatcher disabled") — it never triggers evaluations.
- `services/control_api/models/schemas.py`:
  - Add `DispatcherStatus`, `DispatcherRecommendation`, `DispatcherBlockedTicket`, `DispatcherResponse` Pydantic models matching the service output.
- `services/control_api/main.py`:
  - `app.include_router(dispatcher.router)` and the project-scoped router.
- **No new "launch" endpoint is introduced.** In `manual` mode the UI reuses the existing run-ticket action already exposed by the API; the dispatcher itself stays read-only.

### Frontend — Dispatcher page
- `apps/dashboard/src/api/dispatcher.js` (new):
  - `getDispatcherStatus()`, `getDispatcherRecommendations(projectId)`.
- `apps/dashboard/src/pages/DispatcherPage.jsx` (new):
  - Header: current dispatcher mode badge (`off` / `advisory` / `manual` / `auto`) + last evaluated timestamp.
  - If mode = `off`: render a "Dispatcher is disabled. Set `AI_DEV_FACTORY_DISPATCHER_MODE` to enable advisory recommendations." informational panel and stop.
  - Otherwise two sections:
    - **Recommended execution queue** — table with columns: rank, ticket ID (linking to `TicketDetailPage`), score, difficulty label, queue rank, age, reason.
    - **Blocked tickets** — table with columns: ticket ID, status, blocking step, reason.
  - In `manual` mode each recommendation row shows the existing "Run ticket" action (same React component / handler used elsewhere); no new launch flow is added.
  - Uses the existing `usePolling` hook to refresh every N seconds.
- `apps/dashboard/src/App.jsx`:
  - Register route `/projects/:projectId/dispatcher` → `<DispatcherPage />`.
  - Add a navigation link in the existing sidebar/nav alongside the other project pages.

### Tests
- `tests/test_ticket_dispatcher.py` (new) — unit tests for the service:
  - `off` mode returns empty payload and triggers no eligibility evaluation (assert via spy/mock that `evaluate_eligibility` is not called).
  - `advisory` mode returns ranked READY_TO_TAKE tickets with reasons.
  - Blocked tickets land in `blocked` with the correct `blocking_step` / `reason`.
  - Ranking is deterministic across ties.
  - `get_recommended_tickets` never writes to the DB (snapshot the DB file mtime/contents before & after).
- `tests/test_ticket_dispatcher_api.py` (new) — API tests modeled on `tests/test_ticket_eligibility_api.py`:
  - `GET /dispatcher/status` reports current mode.
  - `GET /projects/{id}/dispatcher/recommendations` returns the expected shape in `advisory` mode.
  - With `AI_DEV_FACTORY_DISPATCHER_MODE` unset, the endpoint reports `mode == "off"` and an empty payload.
- Frontend smoke test (if a test setup already exists for similar pages): mount `DispatcherPage` with a mocked API client and assert the disabled / advisory / manual variants render.

### Documentation
- Brief section added to the existing service overview (or its equivalent in the repo, e.g. an API/README under `services/control_api/` or `tools/agent_runner/`) describing the dispatcher modes, the env var, and the fact that `off` is the default.

## Excluded
- No automatic worker assignment, scheduler, or daemon changes.
- No `auto` mode behavior implementation (the constant is defined; recommendations refuse to act on it).
- No new "launch ticket" endpoint or modification of the existing run-ticket workflow — `manual` mode strictly reuses the existing run action exposed elsewhere in the UI/API.
- No changes to the ticket execution chain, runner, supervisor, or any existing service (`Intelligence`, `Readiness`, `Rules`, `Approval`, `Eligibility`) beyond importing them read-only.
- No new DB tables, migrations, or audit entries for dispatcher activity (it is read-only and stateless).
- No multi-worker support, fairness/quota logic, or persistent dispatcher state.
- No changes to existing tests' assertions; only additive new test files.

## Acceptance criteria
- A `TicketDispatcherService` (module `tools/agent_runner/ticket_dispatcher.py` exposing `get_recommended_tickets(...)`) exists and is importable.
- `AI_DEV_FACTORY_DISPATCHER_MODE` controls the mode; the default is `off`.
- With the env var unset or set to `off`, the dispatcher returns an empty payload without invoking the eligibility/intelligence/readiness services, and no other AI Dev Factory behavior changes (existing ticket execution still works identically; existing tests still pass).
- In `advisory` mode, calling the service returns a ranked list of READY_TO_TAKE tickets with `rank`, `score`, and `reason`, plus a `blocked` list with `blocking_step` and `reason`, computed purely from existing tables and `state.json` files (no DB writes occur during a call — verified by a test).
- In `manual` mode, the dispatcher returns the same recommendations as `advisory`; launching a recommended ticket is performed exclusively through the existing run-ticket UI/API path (no new launch endpoint).
- `GET /dispatcher/status` reports the current mode and the list of available modes.
- `GET /projects/{project_id}/dispatcher/recommendations` returns the documented JSON shape.
- A dedicated Dashboard page is reachable at `/projects/:projectId/dispatcher`, shows the mode, the recommended queue (with score and reasons), and the blocked tickets (with blocking reasons), and clearly indicates when the dispatcher is disabled.
- New tests (`tests/test_ticket_dispatcher.py`, `tests/test_ticket_dispatcher_api.py`) pass; the full existing test suite continues to pass without modification.
- No changes are introduced to the runner, daemon, supervisor, scheduler, or worker code paths.
