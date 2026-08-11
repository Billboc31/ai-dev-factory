All tests green. Implementation complete.

---

## Summary

**Files modified:**

- **`services/control_api/models/schemas.py`** — Added `TicketPipelineRow` model, `BatchPipelineStatusResponse` model, and `pipeline_summary: str | None = None` field to `BatchSummary`.

- **`services/control_api/routes/batches.py`** — Added imports for new schemas; added 5 new functions: `_compute_ticket_blocking`, `_compute_waiting_summary`, `_compute_pipeline_summary`, `_build_pipeline_status`; added `GET /{batch_id}/pipeline-status` and its project-scoped variant; updated `_build_summary` to populate `pipeline_summary`.

- **`apps/dashboard/src/api/batches.js`** — Added `getBatchPipelineStatus(projectId, batchId)`.

- **`apps/dashboard/src/pages/BatchDetailPage.jsx`** — Imports and polls `getBatchPipelineStatus`; renders `<BatchPipelineStatusPanel>` before the analysis summary.

- **`apps/dashboard/src/pages/BatchesPage.jsx`** — Renders `pipeline_summary` as a small italic line below the status badge in each batch row.

**Files created:**

- **`apps/dashboard/src/components/BatchPipelineStatusPanel.jsx`** — Color-coded banner + per-ticket table with intelligence/readiness/runtime/blocking columns.
- **`apps/dashboard/tests/BatchPipelineStatusPanel.test.jsx`** — 5 rendering cases (all passing).
- **`tests/api/test_batch_pipeline_status.py`** — 10 backend integration test cases against the new endpoint (all passing).
