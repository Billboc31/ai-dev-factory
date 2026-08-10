## Objective

Surface per-ticket Ticket Intelligence, readiness, and runtime state on the batch detail page, and add a compact waiting summary to the batch list, so operators can see exactly what a `frozen` batch is waiting on before dependency analysis starts.

## Included

### Backend

**`services/control_api/models/schemas.py`**
- Add `TicketPipelineRow` model: `ticket_id`, `issue_number: int | None`, `title: str | None`, `intelligence_status: str`, `readiness_status: str | None`, `runtime_state: str | None`, `is_blocking: bool`, `blocking_reason: str | None`
- Add `BatchPipelineStatusResponse` model: `batch_id: str`, `batch_status: str`, `waiting_summary: str`, `tickets: list[TicketPipelineRow]`
- Add `pipeline_summary: str | None = None` optional field to `BatchSummary`

**`services/control_api/routes/batches.py`**
- Add `_compute_pipeline_summary(db_path, batch_status: str, ticket_ids: list[str]) -> str | None` helper — uses a single JOIN query to count incomplete intelligence rows; returns a compact string ("Waiting on Ticket Intelligence (3 pending)", "Ready for dependency analysis", etc.); returns `None` for terminal statuses. Used to populate `BatchSummary.pipeline_summary`.
- Add `_build_pipeline_status(db_path, project_root, batch_id, ticket_ids, worktrees_dir) -> BatchPipelineStatusResponse` helper — fetches `ticket_intelligence`, `ticket_readiness`, and `ticket_runtime` rows per ticket using existing `runtime_db.get_ticket_intelligence`, `runtime_db.get_ticket_readiness`, and `_ticket_runtime_map`; titles via `_read_ticket_title`; computes `waiting_summary` and `is_blocking` per ticket; tickets absent from pipeline tables appear with `intelligence_status="not_started"`.
- Add `GET /{batch_id}/pipeline-status` route on `router` returning `BatchPipelineStatusResponse`.
- Add the project-scoped variant on `project_router` under `/{project_id}/dispatcher/batches/{batch_id}/pipeline-status`.
- Update `_build_summary()` to call `_compute_pipeline_summary()` and populate `pipeline_summary`.

**`waiting_summary` string rules (implemented in `_build_pipeline_status`):**
- `collecting` → `"Collecting — {N} member(s) so far"`
- `frozen` + incomplete intelligence → `"Waiting on Ticket Intelligence: {T001}, {T002}, …"`
- `frozen` + all intelligence complete → `"Ready for dependency analysis"`
- `dependency_analysis_running` → `"Dependency analysis running"`
- `dependency_analysis_failed` → `"Dependency analysis failed — retry pending"`
- `readiness_running` → `"Readiness evaluation running"`
- `dispatching` → `"Dispatching tickets"`
- `completed` → `"Batch completed"`

### Frontend

**`apps/dashboard/src/api/batches.js`**
- Add `getBatchPipelineStatus(projectId, batchId)` → `GET /dispatcher/batches/{batchId}/pipeline-status` (with project-scoped path when `projectId` is set, matching the pattern used by `getBatch`).

**`apps/dashboard/src/components/BatchPipelineStatusPanel.jsx`** (new file)
- Prop: `data` (a `BatchPipelineStatusResponse` object), `batchStatus` string.
- Renders a colored banner for `waiting_summary`: yellow when frozen with blocking tickets, green when ready/complete, gray otherwise.
- Renders a table with columns: Ticket ID | Title | Intelligence | Readiness | Runtime State | Blocking reason.
- Status badges use consistent color coding: `not_started` gray, `queued` blue, `running` indigo (animated), `completed` green, `failed` red.
- Missing `readiness_status` (null) displayed as `—` not hidden.
- Missing `runtime_state` (null) displayed as `—` not hidden.

**`apps/dashboard/src/pages/BatchDetailPage.jsx`**
- Import `BatchPipelineStatusPanel` and `getBatchPipelineStatus`.
- Add a `usePolling` call for `getBatchPipelineStatus(projectId, batchId)` alongside the existing polling calls.
- Render `<BatchPipelineStatusPanel>` near the top of the detail layout — before the dependency graph and phases panels — so it is immediately visible; visible for all batch statuses.

**`apps/dashboard/src/pages/BatchesPage.jsx`**
- In each batch card (for the current/next batch display and the list), render `batch.pipeline_summary` as a small italic line below the status badge when the value is non-null.

## Excluded

- Changes to the batch lifecycle state machine or dispatcher logic.
- Triggering or re-queuing intelligence analysis from the UI.
- Modifying existing panels: `BatchAnalysisSummaryPanel`, `BatchDependencyGraph`, `BatchPhasesPanel`, `DispatcherInsightsPanel`.
- Per-ticket intelligence detail panels beyond what `BatchPipelineStatusPanel` provides.
- Sorting, filtering, or pagination of the pipeline status table.
- Real-time WebSocket/SSE updates (existing `usePolling` interval is sufficient).
- Changes to ticket-level intelligence or readiness routes.

## Acceptance criteria

- `GET /dispatcher/batches/{batch_id}/pipeline-status` returns `waiting_summary` string, `batch_status`, and a `tickets` array with `intelligence_status`, `readiness_status`, `runtime_state` for every batch member.
- Tickets absent from `ticket_intelligence` or `ticket_readiness` tables are included in the response with `intelligence_status="not_started"` (not omitted).
- `BatchSummary.pipeline_summary` is non-null for `collecting` and `frozen` statuses and is reflected in `GET /dispatcher/batches` list response.
- Batch detail page renders `BatchPipelineStatusPanel` for all batch statuses; when `frozen` with incomplete intelligence, the banner names the blocking ticket IDs.
- When all tickets have `intelligence_status == "completed"` and batch status is `frozen`, `waiting_summary` is `"Ready for dependency analysis"`.
- Batch list cards show `pipeline_summary` text for `frozen` and `collecting` batches.
- No regressions in existing batch detail panels (graph, phases, insights, analysis summary).
