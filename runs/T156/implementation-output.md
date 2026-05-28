The diff looks right — 4 source files changed as planned. Here's a summary of what was implemented:

---

## Changes made

**`services/control_api/routes/runtime_dashboard.py`**
- Added imports: `resolve_proxy_routes_dir` (infra_service_manager), `build_sandbox_urls` (proxy_manager)
- Extended `SandboxRunSummary` with 8 new fields: `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at`
- Updated `_parse_sandbox_state()` to populate them:
  - `urls` — reads from `state.json`, falls back to `build_sandbox_urls(sandbox_id)`
  - `proxy_ready` — checks existence of `{proxy_routes_dir}/{sandbox_id}.yml`
  - `healthcheck_status`, `smoke_status`, `failing_step`, `last_checked_at` — read from `validation.json` with try/except guard (absent file → all `None`)
  - `ref` — reads `ref`/`branch`/`commit` from `state.json`
  - `created_at` — reads `created_at` key separately from `started_at`

**`apps/dashboard/src/api/runtimeDashboard.js`**
- Added `stopSandboxRun(id)` — needed for the Stop action button

**`apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`**
- Replaced flat table with `EnvironmentCard` components per sandbox
- Each card shows: pretty URLs (web + API) first with copy + open buttons, collapsible debug ports, proxy/healthcheck/smoke status chips, ref badge, failing step banner linked to logs, info row (compose/runtime/worktree/timestamps), Stop + Delete + View Logs actions with confirmation dialogs

**`apps/dashboard/src/pages/RuntimeDashboardPage.jsx`**
- Section title changed from "Sandbox Runs" to "Running Environments"
