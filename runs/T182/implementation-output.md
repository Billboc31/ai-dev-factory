Implementation complete. Here's a summary of all changes:

---

## Summary

**Files modified:**
- `apps/dashboard/src/App.jsx` — Replaced flat routing + top nav with `AppLayout` using project-scoped routes (`/projects/:projectId/*`), localStorage + URL sync for active project, `Navigate` redirect from `/` to `/projects`
- `apps/dashboard/src/components/ProjectSidebar.jsx` — Full workspace sidebar: project list, per-project nav section (Dashboard/Tickets/Worktrees/Logs/Daemon), global section (Runtime/Environments/Sandboxes)
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Reads `projectId` from URL params instead of context; back link updated to `/projects/:projectId/tickets`
- `apps/dashboard/tests/TicketDetail.test.jsx` — Updated to new route pattern `/projects/:projectId/tickets/:id`, fixed API assertions
- `apps/dashboard/tests/TicketDetailPage.test.jsx` — Updated route + fixed `getTicketState` → `getTicketPlan` assertion mismatch

**Files created:**
- `apps/dashboard/src/pages/ProjectDashboardPage.jsx` — Project info, daemon status card, runtime status, stats (active tickets/workers), daemon controls, activity feed
- `apps/dashboard/src/pages/ProjectTicketsPage.jsx` — Per-project ticket list via URL params, ticket detail links to `/projects/:projectId/tickets/:id`
- `apps/dashboard/src/pages/ProjectWorktreesPage.jsx` — Daemon board columns + branches list
- `apps/dashboard/src/pages/ProjectLogsPage.jsx` — Two tabs: Daemon Logs (activity feed) and Runtime Status (paths with copy buttons, PID, workers)

**Test results:** 65 pass / 5 fail — the 5 remaining failures are all pre-existing (`DaemonActivityFeed` argument order bug, 4 `RuntimeDashboardPage` UI label mismatches).
