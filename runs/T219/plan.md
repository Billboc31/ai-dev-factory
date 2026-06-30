## Objective
Add a new project-scoped dashboard section that visualizes backlog batches, their state-machine lifecycle, per-ticket dependency analysis results, execution phases, and Dispatcher blocking insights, with a React Flow dependency graph and 10-second auto-refresh. Existing Dispatcher pages stay unchanged.

## Included

### Backend — new read-only batch API (`services/control_api/`)

- New route module `services/control_api/routes/batches.py`:
  - `GET /dispatcher/batches` → list every batch from `runtime_db.list_backlog_batches`, augmented with: `batch_id`, `status`, `ticket_count` (via `list_backlog_batch_ticket_ids`), `created_at`, `frozen_at`, `completed_at`, `last_activity_at`, `freeze_blocked`, `freeze_blocked_reason`, `dependency_analysis_attempts`, `last_dependency_analysis_error`, `next_dependency_analysis_retry_at`, plus a derived `progress` (done / total based on per-ticket states) and `current_phase` (the highest fully-completed `execution_phase` from `ticket_dependency_analysis`).
  - `GET /dispatcher/batches/current` → `{ "current": <dispatching batch summary or null>, "next": <oldest non-completed non-dispatching batch or null> }`.
  - `GET /dispatcher/batches/{batch_id}` → full detail: batch row + per-ticket array. Each ticket row contains: `ticket_id`, `title` (from `runs/<ticket>/ticket.md` first H1 or `runtime_db.get_ticket_runtime`), `status`, `execution_phase`, `parallel_group`, `depends_on`, `blocks`, `conflicting_tickets`, `readiness_state`, `dispatcher_state` (READY_TO_TAKE / BLOCKED / RUNNING / etc., reusing `ticket_dispatcher.get_recommended_tickets` data).
  - `GET /dispatcher/batches/{batch_id}/graph` → graph payload `{ "nodes": [{id, label, status, color_key, execution_phase, parallel_group, selected_by_dispatcher}], "edges": [{from, to, type}] }` built from `ticket_dependency_analysis` rows. `color_key` is one of `done | running | waiting | waiting_human | failed | selected` derived from each ticket's runtime state plus the Dispatcher's current recommendation set.
  - `GET /dispatcher/batches/{batch_id}/phases` → `[{ "phase": 1, "tickets": [ticket_id, ...] }, ...]` grouped from `execution_phase`; tickets without a phase fall under `"phase": null` at the end.
  - `GET /dispatcher/batches/{batch_id}/insights` → `{ runnable: [...], blocked: [{ticket_id, blocked_by}], conflicts: [{ticket_id, conflicts_with}] }`, computed from `get_dependency_analysis` (depends_on / conflicting_tickets) combined with `ticket_dispatcher.get_recommended_tickets`.
  - Mirror project-scoped variants under `/projects/{project_id}/dispatcher/batches[...]` using the existing `resolve_project` / `resolve_project_runtime_root` dependencies and `_resolve_db_for_project` helper pattern from `routes/dispatcher.py`.
  - All endpoints are GET-only and never mutate state.

- New `routes/batches.py` action endpoints (POST, opt-in only when the batch is in the matching state — these wrap existing `backlog_batch.py` helpers, no new lifecycle logic):
  - `POST /dispatcher/batches/{batch_id}/freeze` → call `transition_batch(from_status=COLLECTING, to_status=FROZEN)`. Returns 409 if not in `collecting`.
  - `POST /dispatcher/batches/{batch_id}/retry-dependency-analysis` → call `mark_dependency_analysis_attempt_started` when current status is `dependency_analysis_failed`. Returns 409 otherwise.
  - `POST /dispatcher/batches/{batch_id}/recompute-dependencies` → reset analysis attempts to 0 and transition back to `frozen` so the daemon picks it up; refuse if status is `completed` or `dispatching`.
  - `POST /dispatcher/batches/{batch_id}/cancel` → guarded transition to `completed` with a `cancelled_by_operator` note, refused while `dispatching` to avoid mid-execution mutation (matches T218 invariant).
  - Each action emits a runtime event via `runtime_db.append_runtime_event` (`batch.operator_action`) for traceability.

- New Pydantic schemas in `services/control_api/models/schemas.py`:
  - `BatchSummary`, `BatchListResponse`, `BatchTicketDetail`, `BatchDetailResponse`, `BatchCurrentResponse`, `BatchGraphNode`, `BatchGraphEdge`, `BatchGraphResponse`, `BatchPhase`, `BatchPhasesResponse`, `BatchBlockedTicket`, `BatchConflict`, `BatchInsightsResponse`, `BatchActionResponse`.

- Wire the new routers in `services/control_api/main.py` next to the existing dispatcher routers (`batches.router`, `batches.project_router`).

### Frontend — new dashboard section (`apps/dashboard/`)

- Add the `reactflow` dependency in `apps/dashboard/package.json` (and update `package-lock.json` accordingly).

- New API client `apps/dashboard/src/api/batches.js` with one function per backend endpoint listed above (`listBatches`, `getCurrentNextBatch`, `getBatch`, `getBatchGraph`, `getBatchPhases`, `getBatchInsights`, `freezeBatch`, `retryBatchDependencyAnalysis`, `recomputeBatchDependencies`, `cancelBatch`). All project-scoped variants accept `projectId`.

- New page `apps/dashboard/src/pages/BatchesPage.jsx`:
  - Route `/projects/:projectId/dispatcher/batches` (added in `App.jsx`).
  - Shows the "Current batch / Next batch" overview at the top using `getCurrentNextBatch`.
  - Renders the batch list table with the required columns: `Batch ID | Status | Ticket count | Created at | Last activity | Progress | Current phase`.
  - Each row links to the detail view and exposes action buttons (Open details, Force freeze, Retry dependency analysis, Recompute dependencies, Cancel batch). Buttons are disabled when the status guard would reject the action.
  - Uses `usePolling(fetchAll, 10000, projectId)` for auto-refresh.

- New page `apps/dashboard/src/pages/BatchDetailPage.jsx`:
  - Route `/projects/:projectId/dispatcher/batches/:batchId`.
  - Top section: batch header (id, status, created/frozen/completed timestamps, dependency-analysis state, readiness state).
  - Tickets table with columns `Ticket ID | Title | Status | Execution phase | Dependencies | Readiness state | Dispatcher state`.
  - Embeds the three visual sub-components below.
  - Polls every 10 s.

- New component `apps/dashboard/src/components/BatchDependencyGraph.jsx`:
  - Uses React Flow to render nodes + edges from `getBatchGraph`.
  - Node color mapping: `done → green`, `running → blue`, `waiting → gray`, `waiting_human → orange`, `failed → red`, `selected → purple`.
  - Auto-layouts nodes by `execution_phase` (x = phase index × spacing, y = stacked within phase) so the graph stays readable for dozens of tickets. Pan/zoom controls enabled; minimap shown when >20 nodes.

- New component `apps/dashboard/src/components/BatchPhasesPanel.jsx`:
  - Renders execution phases as a vertical list. Each phase shows its ticket cards; the phase header notes "(parallel)" when it has more than one ticket.

- New component `apps/dashboard/src/components/DispatcherInsightsPanel.jsx`:
  - Three sections: Runnable tickets, Blocked tickets (with `blocked by <id>` reasons), Conflicting tickets (`conflicts with <id>`). All from `getBatchInsights`.

- Update `apps/dashboard/src/components/ProjectSidebar.jsx` — append a `{ label: 'Batches', path: 'dispatcher/batches' }` entry to `PROJECT_NAV` directly after the existing `Dispatcher` entry. Do not remove or rename the existing `Dispatcher` entry.

- Update `apps/dashboard/src/App.jsx`:
  - Register the two new routes (`BatchesPage`, `BatchDetailPage`) inside the existing project-scoped routes block. Do not touch the existing `DispatcherPage` route.

### Tests

- Backend (pytest, alongside existing API tests):
  - `tests/api/test_batches_routes.py`: covers list endpoint shape, detail endpoint shape, current/next selection logic, graph payload nodes+edges, phase grouping, insights computation (mock `ticket_dispatcher.get_recommended_tickets`), and the four POST action guards (200 on valid transition, 409 on invalid status).
- Frontend (vitest):
  - `apps/dashboard/tests/BatchesPage.test.jsx`: mocks `api/batches.js`, asserts the table renders columns and rows, auto-refresh triggers at 10 s, and action buttons are disabled per status.
  - `apps/dashboard/tests/BatchDetailPage.test.jsx`: asserts header, ticket table, phases panel, insights panel, and graph render with mocked data; verifies node color class for each `color_key`.
  - `apps/dashboard/tests/BatchDependencyGraph.test.jsx`: assert node-color mapping helper directly (graph itself is mocked via React Flow stub) — keeps the test stable without rendering real SVG.

## Excluded

- No changes to the existing `/projects/:projectId/dispatcher` page (`DispatcherPage.jsx`) or its API (`api/dispatcher.js`).
- No changes to the batch state machine in `tools/agent_runner/backlog_batch.py` or the analyzer in `tools/agent_runner/global_dependency_analyzer.py`. The dashboard only reads state and calls the existing lifecycle helpers through guarded POSTs.
- No changes to the Dispatcher scoring algorithm or to ticket execution.
- No write paths from the graph view (edges are read-only; users cannot create/edit dependencies in the UI).
- No new mode for the Dispatcher and no change to `AI_DEV_FACTORY_DISPATCHER_MODE` semantics.
- No global (non-project-scoped) variant of the batches page — batches are inherently per-project, mirroring the existing project-scoped Dispatcher.
- No mobile/responsive redesign — desktop layout consistent with existing dashboard pages is enough.
- No persistence of UI preferences (filters, graph zoom level) across sessions.

## Acceptance criteria

- Navigating to `/projects/<project>/dispatcher/batches` renders the new page; the existing `/projects/<project>/dispatcher` page still renders unchanged.
- The page lists every batch returned by `GET /projects/<project>/dispatcher/batches` with the seven required columns.
- The "Current batch / Next batch" overview shows the active `dispatching` batch (or `null`) and the next non-completed batch.
- Selecting a batch opens a detail view that displays the per-ticket table with `Ticket ID | Title | Status | Execution phase | Dependencies | Readiness state | Dispatcher state`.
- A React Flow graph renders one node per ticket and one edge per dependency relationship; node colors follow the mapping `done=green / running=blue / waiting=gray / waiting_human=orange / failed=red / selected=purple`.
- An execution-phases panel groups tickets by their `execution_phase` and labels phases with more than one ticket as parallel.
- A Dispatcher insights panel lists runnable tickets, blocked tickets with `blocked by <id>` reasons, and conflicting tickets.
- The page auto-refreshes every 10 seconds (verified by `usePolling` invocation interval in the test).
- The action buttons (Force freeze, Retry dependency analysis, Recompute dependencies, Cancel batch) invoke the corresponding POST endpoints; backend returns 409 when the batch is in an incompatible status and the UI surfaces that error via `ErrorBanner`.
- Backend pytest suite for `routes/batches.py` passes (`pytest tests/api/test_batches_routes.py`).
- Frontend `npm test` passes including the three new test files.
- Rendering remains usable with ≥ 30 tickets in a batch (graph supports pan/zoom; table paginates implicitly via overflow scroll).
- No other dashboard page, no other route, and no existing test is modified or broken.
