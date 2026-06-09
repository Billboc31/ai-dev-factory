# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T182/reviews/implementation-review.md
- generated at: 2026-06-09T16:09:58Z

---

I have all the context needed. Here is the review.

---

# PR Review — T182: Multi-project workspace UI

## Résumé

T182 introduces project-scoped routing (`/projects/:projectId/*`), a full workspace sidebar, and four new pages: `ProjectDashboardPage`, `ProjectTicketsPage`, `ProjectWorktreesPage`, and `ProjectLogsPage`. The implementation is architecturally correct and covers the core acceptance criteria. Two issues require a fix before approval: a React Fragment key bug in the tickets table and the absence of new tests promised by the plan.

---

## Vérifications effectuées

- `App.jsx` — routing restructure, `ActiveProjectContext`, localStorage/URL sync
- `ProjectSidebar.jsx` — workspace sidebar, per-project nav, global nav
- `ProjectDashboardPage.jsx` — project info, daemon controls, stat cards, activity feed
- `ProjectTicketsPage.jsx` — ticket list, state badges, conflict detail rows
- `ProjectWorktreesPage.jsx` — daemon board columns, branch table
- `ProjectLogsPage.jsx` — daemon logs tab, runtime status tab with path copy
- `TicketDetailPage.jsx` — projectId extraction from URL params
- `runs/T182/plan.md` — plan compliance check
- Ticket acceptance criteria — line-by-line

---

## Points validés

**Routing**
- `/` → `/projects` redirect in place.
- All project-scoped routes match the plan: `/projects/:projectId/{dashboard,tickets,tickets/:id,worktrees,logs,daemon}`.
- Legacy routes kept for non-migrated pages — correct scoping decision per plan exclusions.

**Active project context**
- localStorage persistence initialised on mount.
- URL-driven sync via `location.pathname` effect (URL is source of truth).
- Auto-selection of first project when no stored value is present.
- `handleSelectProject` navigates + updates context atomically.

**Sidebar**
- Dark theme, section separation, per-project nav conditioned on `activeProject`.
- `NavLink` active-state highlighting via `navItemClass` callback — correct.
- `+` import shortcut present and correctly routed.

**ProjectDashboardPage**
- Displays: project name, stack badge, root path, runtime root — all required.
- Daemon status card: running/stopped indicator, PID, uptime, current ticket, last heartbeat.
- Start / Stop / Restart daemon actions with `onSuccess` refresh — correctly wired.
- `Re-import` calls `importProject(project.root, projectId)` — correct.
- `hostCommand` banner for out-of-container daemon startup — useful addition.
- StatCards for active tickets and active workers — counts derived from real API data.
- `RuntimeStatusPanel` + `DaemonActivityFeed` reused — good composition.

**ProjectTicketsPage**
- Per-project ticket list via `listTickets(projectId)`.
- State badge colour-coding covers all known states including conflict variants.
- `ConflictDetail` inline expansion with `markConflictFailed` action — within scope.
- Polling at 5 s — appropriate for ticket state updates.
- `Link` to `/projects/:projectId/tickets/:id` — correctly scoped.

**ProjectWorktreesPage**
- Daemon board rendered as column grid; only non-empty columns shown — clean.
- Branches not in the board shown in a separate table — useful fallback.
- `loading` guard prevents flash of empty state — correct.

**ProjectLogsPage**
- Two-tab layout: Daemon Logs / Runtime Status — clean separation.
- Runtime paths (`runtime_root`, `daemon_log`, `supervisor_log`, `socket_path`, `pid_file`) with clipboard copy buttons — satisfies "no shell access required" criterion.
- Active workers list with PID and state.
- Last error rendered in `pre` with `whitespace-pre-wrap` — readable.

**TicketDetailPage**
- `projectId` correctly extracted from `useParams()`.
- Back link points to `/projects/:projectId/tickets` — correct.
- All API calls pass `projectId` — consistent.

---

## Problèmes détectés

### [BLOCKING] React Fragment missing `key` — `ProjectTicketsPage.jsx:130`

```jsx
{tickets.map(t => (
  <>                              // ← Fragment has no key
    <tr key={t.ticket_id}>       // ← key here is on child, not on root element
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </>
))}
```

The shorthand `<>` fragment does not accept a `key` prop. React requires the key on the top-level element returned from each `map()` call. Without it, React cannot track rows across re-renders and will log "Each child in a list should have a unique key prop" for every render. More importantly, when a conflict row expands or collapses, React may reconcile against the wrong fragment, causing incorrect DOM state.

**Fix:**

```jsx
{tickets.map(t => (
  <React.Fragment key={t.ticket_id}>
    <tr className="border-t border-gray-100 hover:bg-gray-50">
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </React.Fragment>
))}
```

`React` must be imported or the component must use the named import: `import React from 'react'` (or `import { Fragment } from 'react'` and use `<Fragment key={…}>`).

---

### [BLOCKING] New unit tests absent — plan acceptance criteria not met

The plan explicitly includes:

> - Unit tests for `ProjectDashboardPage` (mock API, assert daemon start/stop buttons)
> - Unit test for sidebar NavLink active-state logic
> - Update existing routing tests for new URL structure
> - `npm run test` passes (existing + new tests)

Only existing routing tests were updated (`TicketDetail.test.jsx`, `TicketDetailPage.test.jsx`). No new test files were created for `ProjectDashboardPage`, `ProjectSidebar`, `ProjectTicketsPage`, `ProjectWorktreesPage`, or `ProjectLogsPage`.

This is not a stylistic concern — the plan committed to tests as a delivery condition and as an acceptance criterion.

---

### [MINOR] Supervisor log content not viewable

The ticket requires: "supervisor logs" in the logs view. The `ProjectLogsPage` Runtime Status tab displays `supervisor_log` as a copyable path but provides no content viewer. Daemon log content is readable via `DaemonActivityFeed`. Supervisor log content is not. The path display partially satisfies the requirement but doesn't allow inspection without shell access — which the ticket explicitly wants to avoid.

This is non-blocking if accepted as a follow-up, but should be acknowledged.

---

### [MINOR] Settings sidebar link missing — plan says "link present but page out of scope"

Plan's excluded section: _"Settings page implementation (sidebar link present but page out of scope)"_ — meaning the link should appear in the sidebar but need not be functional. The plan's sidebar spec also lists "Settings" as a nav item. The implementation omits the link entirely. This is a minor deviation from the plan's stated approach.

---

### [OBSERVATION] `eslint-disable-line react-hooks/exhaustive-deps` in `App.jsx:46,54`

Both `useEffect` hooks intentionally omit `activeProject` from their dependency arrays to avoid loops. This is the correct engineering choice here — the stale closure is safe because the second effect only runs when `projects.length > 0 && !activeProject` is true at effect invocation time. The disable comments are honest annotations. No change required, but worth flagging that reviewers understand the intent.

---

## Risques éventuels

- **React key bug** could produce subtle DOM mismatches on the tickets table when conflict rows toggle, especially with fast polling (5 s). In a conflict-heavy workflow this becomes a visible rendering defect.
- **Missing tests** leave `ProjectDashboardPage` daemon start/stop wiring entirely unverified. A future refactor could silently break these buttons with no regression signal.
- Legacy routes (`/board`, `/project-map`, etc.) continue to receive `activeProject` via props from the `AppLayout` closure — correct for now but creates a maintenance seam if these pages are migrated later.

---

## Décision

REQUEST_CHANGES — two fixes required before merge.

## Actions demandées

1. **Fix React Fragment key in `ProjectTicketsPage.jsx:130`**: Replace `<>` with `<React.Fragment key={t.ticket_id}>` (and `</>` with `</React.Fragment>`). Ensure `React` is imported.

2. **Write the committed tests**: At minimum —
   - `ProjectDashboardPage.test.jsx`: mock `getDaemonStatus`, `startDaemon`, `stopDaemon`; assert buttons render and invoke correct API.
   - `ProjectSidebar.test.jsx`: assert per-project nav renders when `activeProject` is set, is absent when not.
   - Routing smoke test for at least one `/projects/:projectId/*` route.

3. *(Optional, can be follow-up)* Add a supervisor log content tab or note in the ticket that viewing supervisor log content requires a follow-up ticket.

---

IMPLEMENTATION_FIX_REQUIRED
