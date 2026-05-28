Now I have enough context to write the plan.

## Objective

Extend the Runtime tab so that each sandbox environment card prominently displays pretty proxy URLs and access information, with healthcheck/smoke/proxy status visible at a glance, while keeping fallback ports available as secondary debug info.

## Included

### Backend — `services/control_api/routes/runtime_dashboard.py`

- Extend the `SandboxRunSummary` Pydantic model with new optional fields:
  - `urls: dict[str, str]` — pretty proxy URLs (web + api), sourced from `SandboxState.urls`
  - `ref: str | None` — branch/commit/ref deployed, sourced from worktree state or sandbox state
  - `proxy_ready: bool | None` — derived from whether the proxy route file exists in the proxy routes dir
  - `healthcheck_status: str | None`, `smoke_status: str | None`, `failing_step: str | None` — read from `validation.json` when present (expected location: `{sandbox_dir}/validation.json`)
  - `created_at: str | None` — already on `SandboxState`, expose in summary
  - `last_checked_at: str | None` — read from `validation.json` if present, else `None`
- Update the `_sandbox_run_summary()` builder function to populate all new fields; load `validation.json` with a try/except guard (file absent → all three fields `None`)
- Derive `proxy_ready` by checking existence of `{proxy_routes_dir}/{sandbox_id}.yml` using the existing `runtime_resolver`

### Frontend — `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`

- Rename/replace the flat table layout with an `EnvironmentCard` sub-component rendered per sandbox:
  - **Primary row**: pretty web URL + pretty API URL, each with a copy-to-clipboard button and an "open" button; if URLs are absent show a "no proxy" badge
  - **Secondary collapsible section** ("Debug / Ports"): raw `localhost:port` for web and api ports
  - **Info row**: `project_id`, `compose_project`, `ref` (branch/commit), `runtime_root`, `worktree_path`
  - **Status chips**: running/stopped/failed, proxy ready (green/grey), healthcheck status, smoke status
  - **Timestamps**: `created_at`, `started_at`, `last_checked_at`
  - **Failing step banner**: shown only when `failing_step` is non-null (links to log drawer)
  - **Action buttons**: Open Web, Open API, Copy URL, Refresh, View Logs, Stop, Delete
- Keep the existing `LogViewerDrawer.jsx` wiring unchanged

### Frontend — `apps/dashboard/src/pages/RuntimeDashboardPage.jsx`

- Minor: replace the section title/description to reflect "Environments" framing; no structural change to polling or layout

### Frontend — `apps/dashboard/src/api/runtimeDashboard.js`

- No changes needed; new fields flow through the existing `GET /api/runtime-dashboard/sandbox-runs` response automatically

## Excluded

- Changes to `SandboxManager`, `SandboxState` model, or port allocation logic
- Changes to proxy infrastructure, Traefik config, or route creation
- `ProposalRunsTable` and `RuntimeHealthPanel` components
- New API endpoints (only existing endpoint payloads are extended)
- Backend stop/delete/restart handler logic
- Creating or writing `validation.json` — only reading it when present
- Multi-project or remote sandbox support beyond what `runtime_resolver` already provides

## Acceptance criteria

- `SandboxRunSummary` serializes `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at`; a sandbox with no `validation.json` returns `null` for those three fields without error
- `GET /api/runtime-dashboard/sandbox-runs` returns the new fields for at least one active sandbox in a local test run
- Runtime tab renders one card per sandbox; web and API pretty URLs appear above the fold without scrolling
- Ports are visible only inside the collapsed "Debug / Ports" section
- Copy-to-clipboard button copies the pretty URL string
- Status chips correctly reflect `running`/`stopped`/`failed` and `proxy_ready` true/false
- When `failing_step` is set, a banner is displayed on the card
- All existing stop, delete, and log-viewer actions continue to work
- UI renders without JS errors when the sandbox list is empty
