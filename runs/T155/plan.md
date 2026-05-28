Now I have enough context to write the plan.

## Objective

Redesign the Runtime tab (`SandboxRunsTable` + supporting backend) so that each sandbox/environment card prominently shows its pretty proxy URLs and consolidated status, turning the Runtime tab into the canonical access dashboard for running environments.

## Included

**Backend — `/services/control_api/routes/runtime_dashboard.py` and helpers:**

- Extend `SandboxRunSummary` (or equivalent Pydantic model) to include:
  - `web_url`, `api_url` (pretty proxy URLs read from `validation.json` → `proxy_urls`)
  - `healthcheck_status`, `smoke_status`, `failing_step` (from `validation.json`)
  - `proxy_ready` (bool, derived from `validation.json` or proxy state)
  - `ref` / `commit` / `branch` if present in state or worktree metadata
  - `created_at`, `started_at`, `last_checked_at` timestamps from `validation.json` or `state.json`
  - `compose_project` (already present — verify it is exposed)
  - `worktree_path` (already present — verify it is exposed)
- Update `_parse_sandbox_state()` (in `runtime_dashboard.py` or `runtime_resolver.py`) to read and merge `validation.json` fields into the returned object when the file exists.
- No new endpoints required — enriched data flows through existing `GET /runtime-dashboard/sandbox-runs`.

**Frontend — `/apps/dashboard/src/api/runtimeDashboard.js`:**

- No structural change needed; the richer payload is handled automatically.

**Frontend — `/apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`:**

- Redesign the per-row (or per-card) layout:
  - **Primary block**: `web_url` and `api_url` as large, clickable links with copy-to-clipboard buttons; shown first.
  - **Status badges row**: running/stopped/failed · proxy ready · healthcheck status · smoke status.
  - **Meta row**: sandbox id, ref/commit/branch (if known), compose project, worktree path.
  - **Timestamps row**: created · started · last checked (relative or absolute).
  - **Fallback ports**: collapsible section below the main block, labelled "Debug / fallback ports".
  - **Actions**: open web URL, open API URL, copy URL, refresh, view logs, stop, delete — each as an icon button with a tooltip.
  - **Failed state callout**: when status is `failed`, display `failing_step` inline and a direct link to logs.
- Keep existing `ConfirmDialog` usage for stop/delete actions.
- Keep existing polling cadence from `RuntimeDashboardPage` (5 s).

**Frontend — `/apps/dashboard/src/pages/RuntimeDashboardPage.jsx`:**

- No structural change; may need minor prop threading if `SandboxRunsTable` receives new action callbacks (refresh single row).

## Excluded

- Redesign of `ProposalRunsTable`, `RuntimeHealthPanel`, or `LogViewerDrawer`.
- Changes to port allocation logic or supervisor implementation.
- New backend endpoints or authentication.
- Mobile-responsive layout beyond what Tailwind provides by default.
- Historical / archived sandbox runs (only active/recent runs as currently listed).
- Any change to how proxy URLs are generated or assigned.

## Acceptance criteria

- `GET /runtime-dashboard/sandbox-runs` returns `web_url`, `api_url`, `healthcheck_status`, `smoke_status`, `failing_step`, `proxy_ready`, `created_at`, `started_at`, `last_checked_at` for each sandbox where `validation.json` is present; fields are `null` when the file is absent.
- Runtime tab displays `web_url` and `api_url` as the top-level visual element for each sandbox row/card; each URL has a copy button and an "open in browser" link.
- Fallback ports are rendered but hidden by default behind a collapsible toggle.
- Status area shows at least four badges: overall status (running/stopped/failed), proxy ready (yes/no), healthcheck status, smoke status.
- When `failing_step` is non-null the card renders it as an inline callout with a shortcut to the log viewer.
- `ref`/`branch`/`commit`, compose project, worktree path, and timestamps are visible in each card when available.
- Stop and delete actions remain functional and use the existing confirm dialog.
- A manual refresh button triggers an immediate re-fetch without waiting for the 5 s poll.
- The UI renders correctly when `validation.json` is absent (all new fields degrade gracefully to "—" or hidden).
- Existing `RuntimeHealthPanel` and `ProposalRunsTable` are unaffected.
