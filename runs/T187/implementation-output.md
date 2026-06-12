Everything looks correct. Here's a summary of the 4 files changed to fix the blocking issue:

**`services/control_api/models/schemas.py`** — Added `github_repo: str | None = None` to `ProjectInfo`.

**`services/control_api/routes/projects.py`** — Added `_read_github_repo()` that parses `--issue-repo` from `.ai-dev-factory/deploy.yml` via regex, and wires it into `list_projects` alongside the existing `stack` enrichment.

**`apps/dashboard/src/api/projects.js`** — Added `getProject(projectId)` that calls `listProjects()` and filters by name, returning the matching project or `null`.

**`apps/dashboard/src/pages/ProjectTicketsPage.jsx`** — Added a `useEffect` that fetches project metadata on mount and stores `github_repo` in local state; passes it as `githubRepo` prop to `TicketPreviewPanel`.

With these changes, `TicketPreviewPanel` will receive `githubRepo` (e.g. `Billboc31/ai-dev-factory`) and correctly render the GitHub issue hyperlink and "Open GitHub issue" button for any ticket that has an `issue_number`.
