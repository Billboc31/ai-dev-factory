## Objective

Surface per-ticket Ticket Intelligence, readiness, and runtime state on the batch detail page, and add a compact waiting summary to the batch list, so operators can see exactly what a `frozen` or `readiness_running` batch is waiting on — with deterministic per-ticket blocking rules derived entirely from the backend.

## Included

### Backend

**`services/control_api/models/schemas.py`**
- Add `TicketPipelineRow` model: `ticket_id`, `issue_number: int | None`, `title: str | None`, `intelligence_status: str`, `readiness_status: str | None`, `runtime_state: str | None`, `is_blocking: bool`, `blocking_reason: str | None`
- Add `BatchPipelineStatusResponse` model: `batch_id: str`, `batch_status: str`, `waiting_summary: str`, `tickets: list[TicketPipelineRow]`
- Add `pipeline_summary: str | None = None` optional field to `BatchSummary`

**`services/control_api/routes/batches.py`**

*`_compute_ticket_blocking(batch_status: str, intelligence_status: str, readiness_status: str | None) -> tuple[bool, str | None]`* — pure function returning `(is_blocking, blocking_reason)` for a single ticket given the current batch stage. Deterministic rules:

| Batch status | Condition | `is_blocking` | `blocking_reason` |
|---|---|---|---|
| `frozen` | `intelligence_status == "not_started"` | `True` | `"Intelligence not started"` |
| `frozen` | `intelligence_status == "queued"` | `True` | `"Intelligence queued"` |
| `frozen` | `intelligence_status == "running"` | `True` | `"Intelligence running"` |
| `frozen` | `intelligence_status == "failed"` | `True` | `"Intelligence failed"` |
| `frozen` | `intelligence_status == "completed"` | `False` | `None` |
| `readiness_running` | `readiness_status == "not_started"` | `True` | `"Readiness not started"` |
| `readiness_running` | `readiness_status == "queued"` | `True` | `"Readiness queued"` |
| `readiness_running` | `readiness_status == "running"` | `True` | `"Readiness running"` |
| `readiness_running` | `readiness_status == "failed"` | `True` | `"Readiness failed — cannot dispatch"` |
| `readiness_running` | `readiness_status == "completed"` | `False` | `None` |
| any other status | — | `False` | `None` |

`runtime_state` is always informational; it never contributes to `is_blocking`.

*`_compute_waiting_summary(batch_status: str, tickets: list[TicketPipelineRow]) -> str`* — derives the batch-level summary from `batch_status` and the already-populated `tickets` list (using `is_blocking` and `ticket_id`). Rules:

- `collecting` → `"Collecting — {N} member(s) so far"`
- `frozen` + ≥1 blocking ticket → `"Waiting on Ticket Intelligence: {T001}, {T002}, …"` (IDs of blocking tickets, sorted)
- `frozen` + no blocking tickets → `"Ready for dependency analysis"`
- `dependency_analysis_running` → `"Dependency analysis running"`
- `dependency_analysis_failed` → `"Dependency analysis failed — retry pending"`
- `readiness_running` + ≥1 blocking ticket → `"Waiting on readiness: {T003}, {T006}, …"` (IDs of tickets where `is_blocking`, sorted)
- `readiness_running` + no blocking tickets → `"Readiness complete — awaiting dispatch"`
- `dispatching` → `"Dispatching tickets"`
- `completed` → `"Batch completed"`

*`_compute_pipeline_summary(db_path, batch_status: str, ticket_ids: list[str]) -> str | None`* — lightweight variant for the batch list. Uses a single JOIN query; returns `None` for terminal statuses. Covers both intelligence-blocking and readiness-blocking stages:
- `frozen` + incomplete intelligence rows → `"Waiting on Ticket Intelligence ({N} pending)"`
- `frozen` + all complete → `"Ready for dependency analysis"`
- `readiness_running` + incomplete readiness rows → `"Waiting on readiness ({N} pending)"`
- other non-terminal statuses → appropriate short string per the `_compute_waiting_summary` rules above

*`_build_pipeline_status(db_path, project_root, batch_id, ticket_ids, worktrees_dir) -> BatchPipelineStatusResponse`* — fetches `ticket_intelligence`, `ticket_readiness`, and `ticket_runtime` rows per ticket using existing `runtime_db.get_ticket_intelligence`, `runtime_db.get_ticket_readiness`, and `_ticket_runtime_map`; titles via `_read_ticket_title`; calls `_compute_ticket_blocking` for each ticket; calls `_compute_waiting_summary` over the populated list. Tickets absent from `ticket_intelligence` appear with `intelligence_status="not_started"` and are treated as blocking during `frozen`. Tickets absent from `ticket_readiness` appear with `readiness_status=None` and are treated as `"not_started"` blocking during `readiness_running`.

- Add `GET /{batch_id}/pipeline-status` route on `router` returning `BatchPipelineStatusResponse`.
- Add the project-scoped variant on `project_router` under `/{project_id}/dispatcher/batches/{batch_id}/pipeline-status`.
- Update `_build_summary()` to call `_compute_pipeline_summary()` and populate `pipeline_summary`.

### Backend tests

**`tests/services/control_api/test_batch_pipeline_status.py`** (new file)

Cover the following cases against `_compute_ticket_blocking` and `_build_pipeline_status` / `_compute_waiting_summary`:

1. `frozen` + ≥1 incomplete intelligence rows → `waiting_summary` lists blocking ticket IDs; those tickets have `is_blocking=True` and correct `blocking_reason`.
2. `frozen` + all `intelligence_status == "completed"` → `waiting_summary == "Ready for dependency analysis"`; all tickets have `is_blocking=False`.
3. `readiness_running` + ≥1 ticket with `readiness_status != "completed"` → `waiting_summary == "Waiting on readiness: …"` naming those IDs; blocking tickets have `is_blocking=True`.
4. `readiness_running` + all `readiness_status == "completed"` → `waiting_summary == "Readiness complete — awaiting dispatch"`; no ticket is blocking.
5. Ticket absent from `ticket_intelligence` table → appears in response with `intelligence_status="not_started"` and `is_blocking=True` during `frozen`.
6. Ticket absent from `ticket_readiness` table → appears with `readiness_status=None` displayed as `—`; treated as blocking during `readiness_running`.
7. `intelligence_status == "failed"` during `frozen` → `blocking_reason == "Intelligence failed"` and `is_blocking=True`.
8. `readiness_status == "failed"` during `readiness_running` → `blocking_reason == "Readiness failed — cannot dispatch"` and `is_blocking=True`.
9. `dispatching` batch → all tickets have `is_blocking=False` and `blocking_reason=None` regardless of intelligence/readiness values.
10. `runtime_state` field is populated for display but never causes `is_blocking=True`.

### Frontend

**`apps/dashboard/src/api/batches.js`**
- Add `getBatchPipelineStatus(projectId, batchId)` → `GET /dispatcher/batches/{batchId}/pipeline-status` (with project-scoped path when `projectId` is set, matching the pattern used by `getBatch`).

**`apps/dashboard/src/components/BatchPipelineStatusPanel.jsx`** (new file)
- Prop: `data` (a `BatchPipelineStatusResponse` object), `batchStatus` string.
- Renders a colored banner for `waiting_summary`: yellow when `waiting_summary` starts with `"Waiting on"`, green when `"Ready"` or `"complete"`, gray otherwise.
- Renders a table with columns: Ticket ID | Title | Intelligence | Readiness | Runtime State | Blocking reason.
- Status badges use consistent color coding: `not_started` gray, `queued` blue, `running` indigo (animated), `completed` green, `failed` red.
- `readiness_status == null` displayed as `—`; `runtime_state == null` displayed as `—`.
- `blocking_reason` column: renders text when non-null; empty cell when null. The frontend does not derive blocking state — it renders `is_blocking` and `blocking_reason` as provided by the API.

**`apps/dashboard/src/components/__tests__/BatchPipelineStatusPanel.test.jsx`** (new file)

Cover the following rendering cases:

1. `frozen` + blocking intelligence → yellow banner; blocking IDs visible in banner text; blocking rows show `blocking_reason` in table.
2. `frozen` + all complete → green banner with `"Ready for dependency analysis"`; no blocking reasons shown.
3. `readiness_running` + blocking tickets → yellow banner with `"Waiting on readiness: …"` naming those IDs.
4. Ticket with `readiness_status=null` → cell renders `—` not empty/blank.
5. `dispatching` batch → all `blocking_reason` cells are empty; banner is gray.

**`apps/dashboard/src/pages/BatchDetailPage.jsx`**
- Import `BatchPipelineStatusPanel` and `getBatchPipelineStatus`.
- Add a `usePolling` call for `getBatchPipelineStatus(projectId, batchId)` alongside the existing polling calls.
- Render `<BatchPipelineStatusPanel>` near the top of the detail layout — before the dependency graph and phases panels — visible for all batch statuses.

**`apps/dashboard/src/pages/BatchesPage.jsx`**
- In each batch card, render `batch.pipeline_summary` as a small italic line below the status badge when the value is non-null.

## Excluded

- Changes to the batch lifecycle state machine or dispatcher logic.
- Triggering or re-queuing intelligence/readiness analysis from the UI.
- Modifying existing panels: `BatchAnalysisSummaryPanel`, `BatchDependencyGraph`, `BatchPhasesPanel`, `DispatcherInsightsPanel`.
- Per-ticket intelligence detail panels beyond what `BatchPipelineStatusPanel` provides.
- Sorting, filtering, or pagination of the pipeline status table.
- Real-time WebSocket/SSE updates (existing `usePolling` interval is sufficient).
- Changes to ticket-level intelligence or readiness routes.
- Frontend-side workflow inference: all blocking logic lives in the backend; the UI renders `is_blocking` and `blocking_reason` as received.

## Acceptance criteria

- `GET /dispatcher/batches/{batch_id}/pipeline-status` returns `waiting_summary`, `batch_status`, and a `tickets` array covering every batch member with `intelligence_status`, `readiness_status`, `runtime_state`, `is_blocking`, and `blocking_reason`.
- Tickets absent from `ticket_intelligence` appear with `intelligence_status="not_started"` and `is_blocking=True` when batch is `frozen`.
- Tickets absent from `ticket_readiness` appear with `readiness_status=null` and `is_blocking=True` when batch is `readiness_running`.
- `waiting_summary` is `"Waiting on Ticket Intelligence: …"` listing specific ticket IDs when `frozen` with ≥1 incomplete intelligence row.
- `waiting_summary` is `"Waiting on readiness: …"` listing specific ticket IDs when `readiness_running` with ≥1 ticket whose `readiness_status != "completed"`.
- `waiting_summary` is `"Ready for dependency analysis"` when `frozen` and all intelligence is complete.
- `BatchSummary.pipeline_summary` is non-null for `frozen` and `readiness_running` statuses and is reflected in the `GET /dispatcher/batches` list response.
- All blocking computation passes exclusively through `_compute_ticket_blocking`; the frontend renders `is_blocking` and `blocking_reason` without any workflow inference.
- Batch detail page renders `BatchPipelineStatusPanel` for all batch statuses; yellow banner names blocking ticket IDs when applicable.
- Batch list cards show `pipeline_summary` text for `frozen`, `collecting`, and `readiness_running` batches.
- Backend test suite passes all 10 cases listed above; frontend test suite passes all 5 rendering cases.
- No regressions in existing batch detail panels (graph, phases, insights, analysis summary).
