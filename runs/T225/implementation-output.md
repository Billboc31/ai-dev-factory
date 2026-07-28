All 7 files are accounted for. Here's a summary of what was implemented:

---

## Changes Summary

### Files created (3 new)

**`services/control_api/routes/workspace.py`**
Thin proxy: validates project exists via `resolve_project` dependency, then forwards the request body to the Supervisor's workspace endpoints. Never calls AI, GitHub, or internal services directly.

**`apps/dashboard/src/api/workspace.js`**
Three axios API calls: `postWorkspaceMessage`, `confirmWorkspaceAction`, `confirmWorkspaceIssue` — all routing through `/api/projects/{id}/workspace/*`.

**`apps/dashboard/src/components/ProjectWorkspacePanel.jsx`**
Collapsible right-side panel (w-80, part of the flex layout — survives navigation). Maintains per-project conversation history in component state, resets on project switch. Shows confirmation cards for `actionable` (yellow) and `functional_dev` (blue) responses. Sends only opaque `action_id`/`draft_id` tokens on confirmation — never constructs internal arguments.

### Files modified (4)

**`services/supervisor/main.py`** (+451 lines)
Three new endpoints:
- `POST /workspace/projects/{id}/chat` — loads project context, calls Anthropic API via httpx, classifies intent, stores pending action/draft with UUID, returns structured response.
- `POST /workspace/projects/{id}/actions/confirm` — validates action_id + project match + capability allowlist, then executes via existing Supervisor functions.
- `POST /workspace/projects/{id}/issues/confirm` — validates draft_id + project match, calls `gh issue create`, returns issue URL.

**`services/control_api/main.py`** — imports `workspace` module, registers `workspace.project_router`.

**`apps/dashboard/src/App.jsx`** — adds `workspaceOpen` state, passes toggle to sidebar, renders `<ProjectWorkspacePanel>` as a flex sibling (outside `<Routes>` so it persists across navigation).

**`apps/dashboard/src/components/ProjectSidebar.jsx`** — adds "AI Workspace" toggle button in the project nav section, highlighted when open.

### Known limits

- `rerun_intelligence` and `trigger_deployment` capabilities are registered in the allowlist and proposed by the AI, but their confirmation execution returns a helpful message directing to the platform UI — they require additional context (ticket ID, environment config) not available from the workspace alone.
- Pending actions/issues are stored in-memory only; they are lost on Supervisor restart.
- AI provider is always Anthropic via `ANTHROPIC_API_KEY`; the model defaults to `claude-sonnet-4-6` and is overridable via `WORKSPACE_AI_MODEL` env var.
