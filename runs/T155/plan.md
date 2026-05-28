I have a complete picture of the codebase. Here is the implementation plan.

---

## Objective

Upgrade the Runtime tab sandbox cards to surface pretty URLs as the primary access element, add proxy/healthcheck/smoke status indicators, expose git ref and timestamps, and complete the action set (stop, copy URL, refresh) — all without changing the sandbox creation pipeline or other dashboard sections.

## Included

**`services/control_api/routes/runtime_dashboard.py`**
- Add `ValidationSummary` Pydantic model with fields: `healthcheck_status: str`, `smoke_status: str`, `failing_step: str | None`
- Extend `SandboxRunSummary` with new optional fields: `urls: dict[str, str]`, `created_at: str | None`, `proxy_ready: bool`, `git_ref: str | None`, `validation: ValidationSummary | None`
- Update `_parse_sandbox_state()` to populate all new fields:
  - `urls` — from `state.json["urls"]` (already stored, currently discarded)
  - `created_at` — from `state.json["created_at"]`
  - `proxy_ready` — check existence of `{HOST_RUNTIME_ROOT}/proxy/routes/{sandbox_id}.yml` via `runtime_resolver.get_host_runtime_root()`
  - `git_ref` — read `{worktree_path}/.git/HEAD` if `worktree_path` is set; parse branch name (`ref: refs/heads/<branch>`) or return the raw SHA prefix
  - `validation` — parse `{sandbox_runtime_root}/validation.json` if `sandbox_runtime_root` is set and the file exists

**`apps/dashboard/src/api/runtimeDashboard.js`**
- Add `stopSandboxRun(id)` → `POST /runtime-dashboard/sandbox-runs/{id}/stop`
- Add `restartSandboxRun(id)` → `POST /runtime-dashboard/sandbox-runs/{id}/restart`

**`apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`**
- Replace the flat table with per-sandbox cards; each card contains:
  - **Primary access row**: web URL and API URL as prominent `<a>` links, each with an "Open" button and a "Copy" button (uses `navigator.clipboard.writeText`)
  - **Status row**: main status badge + `proxy_ready` indicator (green dot / grey dot) + `healthcheck_status` badge + `smoke_status` badge (only when `validation` is present)
  - **Meta row**: project_id, compose_project, git_ref (when known), worktree_path (truncated, monospace)
  - **Timestamps row**: created_at, started_at, uptime in human-readable form
  - **Ports section** (collapsible): fallback `key:port` pairs, visible on toggle
  - **Error section**: when status is `error`/`failed` and `validation.failing_step` is set, render a red alert showing the failing step and a direct "View logs" link
  - **Actions bar**: Refresh (triggers `onRefresh` callback), Logs, Stop (POST stop then `onRefresh`; shown only when active), Delete (with confirm dialog; shown only when inactive)
- `SandboxRunsTable` receives an `onRefresh` prop (same as the existing `onDeleted` pattern) wired to `fetchSandboxRuns` in `RuntimeDashboardPage`

**`apps/dashboard/src/pages/RuntimeDashboardPage.jsx`**
- Pass `onRefresh={fetchSandboxRuns}` to `SandboxRunsTable` (alongside the existing `onDeleted`)

## Excluded

- `ProposalRunsTable`, `RuntimeHealthPanel`, `SandboxTopologyPanel` — no changes
- `SandboxState` Pydantic model — no persistence schema change; new fields are read at display time only
- Backend `stop`/`restart` endpoint logic — already implemented, no changes needed
- Proxy route creation or Traefik config — already handled by `run_sandbox.py`
- Any changes to how validation.json is written

## Acceptance criteria

- `GET /api/runtime-dashboard/sandbox-runs` returns `urls`, `proxy_ready`, `git_ref`, `created_at`, and `validation` fields on each item (non-null values whenever the underlying data is present)
- Each sandbox card renders web and API pretty URLs as the first visible element; raw ports are hidden behind a collapsible toggle
- Clicking "Open" on a URL opens it in a new browser tab
- Clicking "Copy" copies the URL to the clipboard without page navigation
- "Stop" button calls the stop endpoint and triggers an immediate data refresh; button is only visible for active sandboxes
- "Refresh" button triggers a manual data fetch
- When `validation` is present, `healthcheck_status` and `smoke_status` are shown as colored badges
- When status is error/failed and `validation.failing_step` is non-null, a red alert block shows the failing step with a "View logs" shortcut
- `proxy_ready` indicator is green when the route file exists, grey otherwise
- `git_ref` is displayed (branch name or short SHA) when `worktree_path` is set and the HEAD file is readable
- The UI contains no project-specific assumptions
