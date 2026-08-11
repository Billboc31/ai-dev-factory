Now I have everything I need to write the review.

---

## Implementation Review — T230: Batch UI: show per-ticket pipeline status while batch is frozen/waiting

### Scope Compliance

The implementation is tightly scoped to the ticket. 21 files changed, with 5 being workflow/run artifacts and the core change touching exactly: `schemas.py`, `batches.py`, one new API function, one new React component, two page updates, two test files. No unrelated refactoring observed.

---

### Backend — `services/control_api/`

**`schemas.py`**

`TicketPipelineRow` and `BatchPipelineStatusResponse` are well-structured. One dead field: `issue_number: int | None = None` is declared in `TicketPipelineRow` but **never populated** in `_build_pipeline_status` and never rendered in the UI. The ticket specifies "ticket id + title/issue number" — the title is populated, so functionally the requirement is met, but the unused schema field is noise for future readers.

**`batches.py` — blocking logic**

`_compute_ticket_blocking` is a pure function with deterministic rules — clean and easy to test. The separation of concerns (compute blocking → compute summary → build response) is correct.

**`batches.py` — `_compute_pipeline_summary` (batch list path)**

This function is called inside `_build_summary` → `_build_summaries`, meaning it runs for **every batch** in the list response. For `frozen` and `readiness_running` statuses, it queries `get_ticket_intelligence` / `get_ticket_readiness` individually per ticket. This is an N+1 query pattern: a batch list with 10 batches of 20 tickets could produce up to 400 extra queries. The function is guarded by the `terminal` early-exit and only fires for active statuses, so it won't blow up post-completion, but it's worth noting for future load.

**`batches.py` — `_build_pipeline_status`**

Correct. `readiness_status` fallback to `None` rather than `"not_started"` is consistent with how the blocking logic handles it (`effective = readiness_status or "not_started"`).

**New endpoints**

Both `GET /{batch_id}/pipeline-status` and the project-scoped variant follow existing patterns exactly (same `_require_db`, `_safe`, `_worktrees_dir_for` usage). 404 handling is consistent.

---

### Frontend — `apps/dashboard/`

**`BatchPipelineStatusPanel.jsx`**

- `bannerClass` uses `waiting_summary.includes('complete')` — this is slightly fragile (would catch a hypothetical future string like "failed: incomplete") but the backend strings are fully controlled, making this safe in practice.
- Null `readiness_status` renders `—`, satisfying the "empty rows shown as not started / not hidden" criterion.
- `is_blocking` highlights rows with `bg-yellow-50`. Blocking reason column shows empty string `''` (not `null`) when non-blocking — this avoids rendering artifacts and is correct.
- Missing: `issue_number` column. Not rendered anywhere. See schema note above.

**`BatchDetailPage.jsx`**

The pipeline status call is added to the existing `Promise.all` in `fetchAll`. This is fetched and refreshed via the existing `usePolling(fetchAll, 10000, ...)` mechanism — correct, no separate polling loop needed. If `getBatchPipelineStatus` fails, `setError` fires and the whole page shows an error. This matches the existing behavior for other endpoints in the same `Promise.all`; acceptable as-is.

**`BatchesPage.jsx`**

The `pipeline_summary` inline note is rendered only when non-null — correctly suppressed for terminal statuses (`completed`, `dependency_analysis_failed` return `None` from `_compute_pipeline_summary`).

---

### Tests

**Backend (`test_batch_pipeline_status.py` — 10 cases)**

Covers: frozen+blocking, frozen+all-complete, readiness+blocking, readiness+all-complete, missing intelligence row, missing readiness row, failed intelligence, failed readiness, dispatching (no blocking), runtime_state informational only. All critical paths covered including the "missing row = not_started" contract.

**Frontend (`BatchPipelineStatusPanel.test.jsx` — 5 cases)**

Covers: yellow banner, green banner, readiness blocking, null readiness renders `—`, dispatching gray banner. Tests use `data-testid` attributes that are present in the component.

---

### Acceptance Criteria Verification

| Criterion | Status |
|---|---|
| Per-ticket intelligence / readiness / runtime status shown | ✅ |
| `frozen` state explains what blocks dependency analysis | ✅ |
| All intelligence complete → transitions to "Ready for dependency analysis" | ✅ |
| Empty/missing pipeline rows shown as not_started, not hidden | ✅ |

---

### Observations (non-blocking)

1. **`issue_number` in `TicketPipelineRow`** — declared, never set, never displayed. Either populate it or remove it to avoid confusion.
2. **N+1 queries in `_compute_pipeline_summary`** — per-ticket DB calls on every batch list response. Acceptable at current scale; worth a note for future optimization if batch lists grow.
3. **`bannerClass` uses `includes('complete')`** — relies on backend string stability. Should stay fine as long as no "complete" substring appears in error/failure strings.

---

IMPLEMENTATION_APPROVED
