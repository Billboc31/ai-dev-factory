All changes look correct. Here's a summary of everything done:

---

## Changes made

**Blocking fix — `TicketDetailPage` project scoping:**

- **`App.jsx`**: Created and exported `ActiveProjectContext`, wrapped `<Routes>` with `<ActiveProjectContext.Provider value={activeProject}>` so the active project is available to all child routes via context.
- **`TicketDetailPage.jsx`**: Imported `useContext` and `ActiveProjectContext`; reads `projectId` from context; passes `projectId` to all `api.*` calls (`getTicket`, tab fetchers, `refreshTicket`, all workflow action buttons, all git/runtime buttons) and to `<AuditLog>`.
- **`AuditLog.jsx`**: Added `projectId` prop; passes it to `getAuditLog(ticketId, projectId)`.

**Non-blocking fixes:**

- **`api/daemon.js`**: Fixed `getDaemonActivity` signature from `(lines = 50, projectId)` to `(projectId, lines = 50)`, consistent with all other functions in the file.
- **`DaemonActivityFeed.jsx`**: Updated call from `getDaemonActivity(lines, projectId)` to `getDaemonActivity(projectId, lines)`.
- **`routes/tickets.py`**: Removed the `_project_worktrees_dir` one-liner wrapper; replaced all 18 usages with direct `resolve_worktrees_dir(project_root)` calls.
