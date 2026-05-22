Implementation complete. Here's a summary of what was created:

**20 pytest tests — all passing**
**9 Vitest tests — all passing**
**0 regressions**

---

## Files created/modified

### Backend (new)
- `services/control_api/routes/runtime_dashboard.py` — FastAPI router at `/runtime-dashboard` with 7 endpoints: list sandbox runs, get logs (with offset), delete sandbox (409 on active/live PID), list proposals, get proposal summary, delete proposal (409 on active), runtime health

### Backend (modified)
- `services/control_api/main.py` — import + `app.include_router(runtime_dashboard.router)`

### Frontend (new)
- `apps/dashboard/src/api/runtimeDashboard.js` — Axios client wrappers for all 7 endpoints
- `apps/dashboard/src/components/runtime-dashboard/ConfirmDialog.jsx` — reusable confirmation modal
- `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx` — table with Open Logs / Delete (disabled when active)
- `apps/dashboard/src/components/runtime-dashboard/ProposalRunsTable.jsx` — table with Open Summary / Delete (disabled when active)
- `apps/dashboard/src/components/runtime-dashboard/RuntimeHealthPanel.jsx` — 4 read-only cards
- `apps/dashboard/src/components/runtime-dashboard/LogViewerDrawer.jsx` — slide-out drawer, polls every 2s via `usePolling`, stops on unmount
- `apps/dashboard/src/components/runtime-dashboard/ProposalSummaryModal.jsx` — modal rendering proposal JSON
- `apps/dashboard/src/pages/RuntimeDashboardPage.jsx` — 4 collapsible sections; polling every 5s for each data source

### Frontend (modified)
- `apps/dashboard/src/App.jsx` — added `RuntimeDashboardPage` import, `<Route path="/runtime-dashboard">`, and "Runtime" nav link

### Tests (new)
- `tests/test_runtime_dashboard_api.py` — 20 pytest cases covering all endpoints including safety checks
- `apps/dashboard/tests/RuntimeDashboardPage.test.jsx` — 9 Vitest cases covering all four sections, disabled/enabled delete states, confirm dialog, log drawer, proposal modal, and health panel
