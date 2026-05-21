Now I have a complete picture of the implementation. Let me write the review.

---

# Review — T125: Project-scoped runtime APIs and daemon isolation

## Summary

The implementation delivers the core objective cleanly. The FastAPI dependency injection pattern (`resolve_project`), explicit `project_root` parameter threading through service functions, and dual-router registration are all well-executed. Test coverage is solid. However, there is one functional gap that violates an acceptance criterion.

---

## Scope compliance

The implementation follows the plan closely. All required components are present:

- `services/control_api/dependencies.py` — `resolve_project` dependency with 404 on unknown project
- Project-scoped routers for daemon, tickets, and project-map
- Frontend API clients updated to accept optional `projectId`
- `useProjects` hook and `ProjectSidebar` component
- `activeProject` state threaded through `App.jsx` to page components
- Unit and integration tests for isolation

Nothing outside the stated scope was added.

---

## Acceptance criteria assessment

| Criterion | Status |
|---|---|
| 404 for unknown `project_id` | PASS — `dependencies.py:16` raises HTTP 404 |
| Independent daemon status per project | PASS — tests confirm via separate `daemon.pid` files |
| Tickets scoped to project root | PASS — `artifact_reader.list_tickets(project_root)` filters by path |
| Project-map scoped per project | PASS |
| Legacy routes still work | PASS — legacy routers preserved, point to `app.state.project_root` |
| Switching project refreshes state | PARTIAL — see blocking issue below |
| Tests validate isolation with two roots | PASS — `test_project_scoped_routes.py`, `test_project_isolation.py` |
| Runtime artifacts not duplicated | PASS — all paths derived from `project_root` |

---

## Blocking issue

### `TicketDetailPage` bypasses project scoping

`App.jsx:51` routes the ticket detail page as:

```jsx
<Route path="/tickets/:id" element={<TicketDetailPage />} />
```

No `projectId` is passed. Inside `TicketDetailPage.jsx:13-19`, all API fetchers ignore the project context:

```javascript
const TAB_FETCHERS = {
  timeline: (id) => api.getTicketTimeline(id),   // no projectId
  logs:     (id) => api.getTicketLogs(id),        // no projectId
  plan:     (id) => api.getTicketPlan(id),        // no projectId
  // ...
}
```

This means every tab in the detail page — logs, plan, review, tests, artifacts, timeline — hits the legacy route (`/api/tickets/{id}/...`), which resolves against `app.state.project_root` (the default/first project), regardless of which project the user has selected.

The same problem affects all action buttons in the detail page (`approve-plan`, `run-next`, `commit`, etc.): they would execute against the wrong project in a multi-project setup where two projects share a ticket ID.

The `tickets.js` API already supports `projectId` as the second argument for all functions — the work is done at the API layer. The detail page just doesn't use it.

**Required fix:** Pass `projectId` to `TicketDetailPage`. The cleanest approach given the existing architecture is React context (since the detail page is rendered without a parent component that can pass props), or store the active project in URL search params so the detail page can read it from `useSearchParams`. A simpler but less clean fix: expose `activeProject` via a context in `App.jsx` and consume it in `TicketDetailPage`.

---

## Observations (non-blocking)

**`getDaemonActivity` parameter order is inconsistent** (`api/daemon.js:8`):

```javascript
export const getDaemonActivity = (lines = 50, projectId) => ...
```

All other functions in `daemon.js` have `projectId` as the first parameter. `DaemonActivityFeed` passes both arguments correctly, so there's no runtime bug. Still worth normalizing.

**Audit log is not project-scoped** (`tickets.py:429`, `tickets.py:240`):

`app.state.db_path` is a single SQLite database shared across all projects. The project-scoped audit log endpoints (`/{project_id}/tickets/{ticket_id}/audit-log`) read from this shared DB. If two projects both have a `T001`, their audit events are stored together and filtered only by `ticket_id`. This is not in the ticket's stated scope, but it is a known gap to document.

**Trivial wrapper adds noise** (`tickets.py:257`):

```python
def _project_worktrees_dir(project_root: Path) -> Path:
    return resolve_worktrees_dir(project_root)
```

This one-liner wrapper is used in every project-scoped ticket route. Calling `resolve_worktrees_dir(project_root)` directly would be cleaner.

---

## Code quality

The backend design is strong: dependency injection is clean, service functions have no hidden global state, and the dual-router pattern for backward compatibility is minimal and explicit. The test suite tests actual behavior rather than just mocks, and the two-project fixture structure is reusable.

The frontend changes are mechanically consistent: the `_pfx` helper and optional parameter pattern are applied uniformly across all three API modules.

---

IMPLEMENTATION_FIX_REQUIRED
