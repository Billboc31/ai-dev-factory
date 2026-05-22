Now I have a clear picture of the codebase. Writing the V1 implementation plan.

## Objective

Add a read-only Runtime Dashboard page to the existing React/FastAPI stack that gives operators visibility into sandbox runs, proposal runs, runtime health, and log tailing, with safe cleanup restricted to completed or failed artifacts only.

## Included

### Backend — `services/control_api/routes/runtime_dashboard.py` (new file)

New FastAPI router registered at `/runtime-dashboard`:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runtime-dashboard/sandbox-runs` | List sandbox runs: id, project\_id, status, started\_at, finished\_at, ports, worktree\_path, compose\_project |
| `GET` | `/runtime-dashboard/sandbox-runs/{id}/logs` | Return sandbox log content with optional `offset` query param for incremental polling |
| `DELETE` | `/runtime-dashboard/sandbox-runs/{id}` | Cleanup sandbox — reject with `409` if status is active or `daemon.lock` holds a live PID |
| `GET` | `/runtime-dashboard/proposal-runs` | List proposal runs: proposal\_id, sandbox\_id, status, changed\_files\_count, started\_at, finished\_at |
| `GET` | `/runtime-dashboard/proposal-runs/{id}` | Open proposal summary (returns proposal state metadata) |
| `DELETE` | `/runtime-dashboard/proposal-runs/{id}` | Delete completed proposal — reject with `409` if active |
| `GET` | `/runtime-dashboard/health` | Return: supervisor\_status (up/down), active\_jobs count, stale\_pid\_files list, stale\_locks list |

Data sources (all generic, no project-specific assumptions):
- Sandbox runs: read `sandboxes/*/state.json`, check `sandboxes/*/daemon.lock`
- Proposal runs: read supervisor HTTP `/auto-fix/{id}/proposals` or equivalent state files under `runs/`
- Runtime health: read `runs/daemon.pid`, scan `runs/*/daemon.lock` for stale locks (PID not alive), scan for orphan `.pid` files
- Safety check helper: shared function that verifies PID liveness from a lock file and rejects cleanup of main runtime paths (`runs/`, `sandboxes/`, repo clone root)

### `services/control_api/main.py`

Register the new `runtime_dashboard` router (one import + one `app.include_router()` call, following the existing pattern).

### Frontend — `apps/dashboard/src/pages/RuntimeDashboardPage.jsx` (new file)

Single page with four collapsible sections:

1. **Sandbox Runs** — table columns: id, status badge, project\_id, started\_at, finished\_at, ports, worktree\_path, compose\_project; per-row actions: Refresh (re-fetches list), Open Logs (opens log drawer), Delete (disabled and visually greyed out if status is active/running)
2. **Proposal Runs** — table columns: proposal\_id, sandbox\_id, status badge, changed\_files\_count, started\_at, finished\_at; per-row actions: Open Summary (fetches and renders proposal state in a modal), Delete (disabled if active)
3. **Runtime Health** — read-only cards: supervisor status indicator, active job count, list of stale pid files, list of stale lock files
4. **Log Viewer** — slide-out drawer triggered by row action; polls `GET /runtime-dashboard/sandbox-runs/{id}/logs?offset=N` every 2 s, auto-scrolls to bottom; polling stops when drawer closes

### New components — `apps/dashboard/src/components/runtime-dashboard/` (new directory)

- `SandboxRunsTable.jsx` — renders sandbox run rows with action buttons
- `ProposalRunsTable.jsx` — renders proposal run rows with action buttons
- `RuntimeHealthPanel.jsx` — read-only health cards
- `LogViewerDrawer.jsx` — slide-out log panel with polling logic and stop-on-close
- `ProposalSummaryModal.jsx` — modal showing proposal state metadata
- `ConfirmDialog.jsx` — reusable confirmation dialog before destructive actions (DELETE)

### `apps/dashboard/src/api/runtimeDashboard.js` (new file)

Typed Axios wrappers using the same `client = axios.create({ baseURL: '/api' })` pattern as existing clients:
- `listSandboxRuns()`, `getSandboxLogs(id, offset)`, `deleteSandboxRun(id)`
- `listProposalRuns()`, `getProposalSummary(id)`, `deleteProposalRun(id)`
- `getRuntimeHealth()`

### `apps/dashboard/src/App.jsx`

Add route `/runtime-dashboard` → `RuntimeDashboardPage` following the existing route declaration pattern.

### `apps/dashboard/src/components/ProjectSidebar.jsx` (or equivalent nav file)

Add "Runtime Dashboard" nav link pointing to `/runtime-dashboard`, styled consistently with existing sidebar links.

### Tests

**`tests/test_runtime_dashboard_api.py`** (new file, pytest):
- `GET /runtime-dashboard/sandbox-runs` returns list with required fields; returns `[]` when no runs exist
- `GET /runtime-dashboard/sandbox-runs/{id}/logs` returns log content; returns `404` for unknown id
- `DELETE /runtime-dashboard/sandbox-runs/{id}` returns `409` when lock holds live PID; returns `204` when lock absent or stale
- `GET /runtime-dashboard/proposal-runs` returns list with required fields
- `DELETE /runtime-dashboard/proposal-runs/{id}` returns `409` for active proposal; `204` for completed
- `GET /runtime-dashboard/health` returns object with keys `supervisor_status`, `active_jobs`, `stale_pid_files`, `stale_locks`

**`apps/dashboard/tests/RuntimeDashboardPage.test.jsx`** (new file, Vitest + React Testing Library):
- Page renders all four sections
- Delete button is disabled when sandbox status is `running`
- Delete button is enabled when status is `completed`; clicking shows confirm dialog
- Log drawer opens when "Open Logs" is clicked; polling stops when drawer is closed
- Proposal summary modal renders proposal metadata on "Open Summary" click

## Excluded

- Sandbox rerun and sandbox stop actions
- Global stale worktree cleanup, stale sandbox directory cleanup, and orphan artifact cleanup automation
- Patch apply and proposal execution
- Automatic merge
- Cloud deployment or remote environment support
- Tester-agent orchestration
- Real-time WebSocket or SSE streaming (polling every 2 s is sufficient)
- Authentication or access control on new endpoints
- Modifications to existing pages (TicketsPage, DeployerPage, SandboxPanel, AutoFixPanel, etc.)
- Any project-specific columns, filters, or rendering logic

## Acceptance criteria

1. `GET /runtime-dashboard/sandbox-runs` returns a JSON list where each item contains at minimum `id`, `status`, `started_at`, `worktree_path`; returns `[]` when no sandbox runs exist.
2. `DELETE /runtime-dashboard/sandbox-runs/{id}` returns `409 Conflict` with an error reason when `daemon.lock` holds a live PID or status is active; returns `204 No Content` when the run is completed or failed.
3. `DELETE /runtime-dashboard/proposal-runs/{id}` returns `409 Conflict` for active proposals; `204 No Content` for completed or failed ones.
4. `GET /runtime-dashboard/health` returns a JSON object containing exactly the keys `supervisor_status`, `active_jobs`, `stale_pid_files`, `stale_locks`.
5. `GET /runtime-dashboard/sandbox-runs/{id}/logs` returns log content; supports `?offset=N` for incremental retrieval.
6. The React page renders at `/runtime-dashboard` and displays the four sections: Sandbox Runs, Proposal Runs, Runtime Health, Log Viewer.
7. Delete action buttons are visually disabled and non-clickable for rows whose status is `running` or `active`.
8. The Log Viewer drawer opens for a sandbox run, displays log content with auto-scroll, and halts polling when closed.
9. `pytest tests/test_runtime_dashboard_api.py` passes with all cases green.
10. `npm run test` in `apps/dashboard/` passes all new Vitest cases green.
11. No existing pytest or Vitest test regresses.
