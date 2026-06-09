Now I have a clear picture of the codebase. Let me produce the plan.

---

## Objective

Build a multi-project workspace UI on top of the T181 foundation by introducing project-scoped routing (`/projects/:projectId/*`), a full workspace sidebar with per-project navigation, a per-project dashboard page, and project-level tickets/worktrees/logs views — replacing the current flat, single-project-centric layout.

## Included

### Routing (`apps/dashboard/src/App.jsx`)
- Restructure routes from flat (`/tickets`, `/daemon`, …) to project-scoped: `/projects/:projectId/dashboard`, `/projects/:projectId/tickets`, `/projects/:projectId/tickets/:id`, `/projects/:projectId/worktrees`, `/projects/:projectId/logs`, `/projects/:projectId/daemon`
- Keep `/projects` (projects index/grid) and `/import-project` as top-level routes
- Redirect `/` to `/projects`
- Persist active project via `localStorage` and synchronise with URL `:projectId` param on navigation

### Workspace sidebar (`apps/dashboard/src/components/ProjectSidebar.jsx`)
- Replace simple project list with a full workspace sidebar
- Top section: projects list with add-project shortcut
- Per-project nav section (visible when a project is selected): Dashboard, Tickets, Worktrees, Logs, Daemon, Settings
- Highlight active route with NavLink
- Show active project name as sidebar header
- Keep dark theme (`bg-gray-800`) consistent with existing style

### `ActiveProjectContext` (`apps/dashboard/src/App.jsx`)
- On load: read `projectId` from localStorage; if absent, default to first project
- On project select from sidebar: update context + localStorage + navigate to `/projects/:projectId/dashboard`
- On route change to `/projects/:projectId/*`: sync context to `:projectId` from URL (source of truth is URL)

### `ProjectDashboardPage` — NEW (`apps/dashboard/src/pages/ProjectDashboardPage.jsx`)
- Display: project name, detected stack, root path, runtime root
- Runtime status cards (reuse/extend `RuntimeStatusPanel`): supervisor state, daemon state, PID, runtime paths
- Counters: active tickets, active worktrees (from daemon board or tickets API)
- Actions: Start daemon, Stop daemon, Restart daemon, Re-import/rescan (POST to existing endpoints)
- Recent activity feed (reuse `DaemonActivityFeed`)
- Polling: 10s for status, 30s for activity

### `ProjectTicketsPage` — NEW (`apps/dashboard/src/pages/ProjectTicketsPage.jsx`)
- Per-project ticket list, scoped to `:projectId` from URL params
- Display: ticket ID, title, state, branch, worktree status
- Adapted from existing `TicketsPage.jsx` but route-driven (no context dependency for project ID)

### `ProjectWorktreesPage` — NEW (`apps/dashboard/src/pages/ProjectWorktreesPage.jsx`)
- Fetch worktree data from `GET /api/projects/:projectId/daemon/board`
- Display per worktree: branch name, ticket, active/idle state, assigned agent
- If endpoint returns no worktree-specific field, display branch list from `GET /api/projects/:projectId/branches` with daemon board data merged

### `ProjectLogsPage` — NEW (`apps/dashboard/src/pages/ProjectLogsPage.jsx`)
- Two tabs: Daemon logs, Runtime events
- Daemon logs: `GET /api/projects/:projectId/daemon/activity` (reuse `DaemonActivityFeed`)
- Runtime status: `GET /api/projects/:projectId/daemon/runtime-status` (display paths, PID, process state)
- Quick-copy path actions (clipboard)
- No shell access required

### `api/projects.js` — extend
- Add `getDaemonRuntimeStatus(projectId)` → `GET /api/projects/:projectId/daemon/runtime-status` if not already present
- Add `getBranches(projectId)` → `GET /api/projects/:projectId/branches` if not already present

### Ticket detail routing
- `TicketDetailPage` adapted to read `projectId` from URL params (`/projects/:projectId/tickets/:id`) instead of from context

### Tests
- Unit tests for `ProjectDashboardPage` (mock API, assert daemon start/stop buttons)
- Unit test for sidebar NavLink active-state logic
- Update existing routing tests for new URL structure

## Excluded

- Backend changes: all required API endpoints already exist from T181
- Environments, deployer, sandbox, auto-fix, and project-map pages — not moved to project-scoped routing in this ticket; they remain accessible from top-level nav or can be addressed in a follow-up
- WebSocket or Server-Sent Events for real-time log streaming — polling is sufficient for this ticket
- Settings page implementation (sidebar link present but page out of scope)
- Any multi-user, auth, or permission layer
- Traefik, sandbox deploys, or deployment tooling

## Acceptance criteria

- Navigating to `/` redirects to `/projects`
- Selecting a project in the sidebar navigates to `/projects/:projectId/dashboard` and highlights the project
- Hard-refreshing `/projects/my-project/tickets` keeps the correct project active (URL is source of truth, persisted to localStorage)
- `ProjectDashboardPage` renders project name, stack, root, runtime root, daemon state, ticket count
- "Start daemon" and "Stop daemon" buttons on the dashboard invoke the correct API endpoints and reflect updated state after polling
- Per-project tickets page (`/projects/:projectId/tickets`) shows only tickets for that project
- Per-project worktrees page shows branch/worktree list from daemon board
- Per-project logs page shows daemon activity and runtime status paths without shell access
- Sidebar nav (Dashboard, Tickets, Worktrees, Logs, Daemon) links are active-highlighted based on current route
- Existing `TicketDetailPage` works under `/projects/:projectId/tickets/:id`
- `npm run test` passes (existing + new tests)
