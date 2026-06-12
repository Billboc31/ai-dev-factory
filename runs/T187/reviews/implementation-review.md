I now have a complete picture. Let me compile the final review.

---

## Review — T187: Restore Ticket Board Workflow (second pass)

### Context

This is the second review pass. The first review returned `IMPLEMENTATION_FIX_REQUIRED` for one blocking issue: `githubRepo` was never passed to `TicketPreviewPanel`, making GitHub issue links dead-wired. The latest commit (`c9a7ef40`) addresses that fix.

---

### Fix verification

The blocking issue is resolved. The fix adds three coordinated changes:

**`apps/dashboard/src/api/projects.js`** — new `getProject(projectId)` helper that fetches the project list and returns the matching project by name.

**`apps/dashboard/src/pages/ProjectTicketsPage.jsx`** — adds `githubRepo` state + a `useEffect` that calls `getProject` and extracts `res.data?.github_repo`, then passes `githubRepo` as a prop to `<TicketPreviewPanel>`.

**`services/control_api/`** — `ProjectInfo` schema gains `github_repo: str | None = None`; `list_projects` now calls `_read_github_repo(project_root_path)` which parses `.ai-dev-factory/deploy.yml` via regex for `--issue-repo`.

The data flow is now complete: backend → list API → `getProject` helper → component state → `TicketPreviewPanel` prop → conditional GitHub links rendered.

---

### Acceptance criteria check

| Criterion | Status |
|---|---|
| 4-column board: Queued / Running / Waiting Human / Done | ✅ |
| Centralized status-to-column mapping in `ticketColumns.js` | ✅ |
| All known states mapped; unknown states fall to Queued | ✅ |
| Waiting Human cards visually distinct (orange ring) | ✅ |
| Click opens preview drawer, no navigation | ✅ |
| Preview: ticket ID, state badge, branch | ✅ |
| Preview: latest activity (`updated_at`) | ✅ |
| Preview: last log | ✅ |
| Preview: last error (via timeline API) | ✅ |
| Preview: linked GitHub issue | ✅ (fixed in this pass) |
| Preview: worktree path | ✅ (placeholder, plan-deferred) |
| Preview: linked PR | ✅ (placeholder, plan-deferred) |
| Preview: ticket title | ⚠️ absent — `TicketSummary` has no `title` field; explicitly plan-deferred |
| Navigation: Open ticket | ✅ |
| Navigation: Open GitHub issue | ✅ (fixed in this pass) |
| Navigation: Open PR | ⚠️ always shown; plan-accepted placeholder |
| Existing `TicketDetailPage` functional | ✅ (untouched) |
| Workspace / multi-project preserved | ✅ |
| 5-second polling preserved | ✅ |

---

### Remaining observations (non-blocking)

**Ticket title** — `TicketSummary` has no `title` field (schema lines 56-69); the preview identifies tickets by ID only. This was explicitly excluded in the plan due to the list API limitation. The gap is real from the ticket's perspective but the plan's deferral is justified. Should be tracked as a follow-up.

**`import re` inside function body** (`routes/projects.py:93`) — Python caches imports so this is not a performance issue, but it's non-idiomatic; the import belongs at the top of the file. Minor style issue only.

**`_read_github_repo` regex heuristic** — parsing `deploy.yml` for `--issue-repo \S+` is fragile if the file format changes. No structural harm for now, but this would be better served by a proper YAML parse or a dedicated config key.

**`stateBadgeClass` substring fallback** (`ticketColumns.js:60`) — `state?.includes(k)` could false-match future states that embed a known state as a substring (e.g. `TESTING_COMPLETE` matching `TESTING`). Not a live bug, but the fallback logic is brittle.

**"Open PR" footer button always visible** — renders even when no PR is associated with the ticket. Label says "Open PR (see ticket detail)" which is slightly misleading. Minor UX; acceptable as a placeholder per plan.

---

### Code quality

`ticketColumns.js` is clean, genuinely centralized, and easy to extend. `TicketPreviewPanel.jsx` handles hook cleanup, loading states, and conditional rendering correctly. `ProjectTicketsPage.jsx` bucketing idiom is simple and readable. The backend addition is minimal and contained.

---

### Summary

The blocking issue from the prior review is resolved correctly. All ticket acceptance criteria are either met or explicitly plan-deferred with documented rationale. The implementation is ready to proceed.

IMPLEMENTATION_APPROVED
