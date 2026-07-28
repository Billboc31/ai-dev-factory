## Objective

Add a persistent AI workspace panel to every project page that routes all user requests through a new workspace endpoint in the Control API (acting as Supervisor gate): informational requests are answered using live project data, actionable requests are dispatched to the Supervisor service only if in an explicit allowlist, and functional development requests are redirected to GitHub issue creation.

## Included

**Backend — `services/control_api/routes/workspace.py`** (new file)
- `POST /projects/{project_id}/workspace/chat` — accepts `{ message: str, conversation_history: list }`, fetches project context (project name, GitHub repo, ticket summary), calls Claude API, classifies the intent as `informational | actionable | functional_dev`, and returns a structured response with `{ reply, intent, proposed_action? }`
- Explicit allowlist of actionable capabilities the endpoint may dispatch on behalf of the workspace: daemon restart, rerun ticket intelligence, rerun dependency analysis, resume execution, trigger deployment — each mapped to the corresponding existing Control API or Supervisor endpoint
- Requests not in the allowlist are refused with a plain-language explanation; functional dev requests receive a reply proposing GitHub issue creation with a draft title and body
- `POST /projects/{project_id}/workspace/create-issue` — takes `{ title: str, body: str }`, calls the GitHub API using the project's configured repo and token, returns `{ issue_url, issue_number }`

**Backend — `services/control_api/main.py`**
- Import and register the `workspace` router

**Frontend — `apps/dashboard/src/api/workspace.js`** (new file)
- `postWorkspaceMessage(projectId, message, history)` → calls `/projects/{projectId}/workspace/chat`
- `createWorkspaceIssue(projectId, title, body)` → calls `/projects/{projectId}/workspace/create-issue`

**Frontend — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`** (new file)
- Collapsible side panel (toggleable, rendered outside `<Routes>` in `AppLayout` so it survives navigation)
- Scrollable message history (user + AI turns)
- Text input + submit button with loading state
- When `intent === functional_dev`: display a "Create GitHub Issue" confirmation card showing the draft title/body; user must confirm before the issue is created
- Conversation history stored in component state, keyed by `projectId` — resets on project switch

**Frontend — `apps/dashboard/src/App.jsx`**
- Render `<ProjectWorkspacePanel projectId={activeProject} />` in `AppLayout` alongside `<main>`, only when `activeProject` is set

**Frontend — `apps/dashboard/src/components/ProjectSidebar.jsx`**
- Add a toggle button or "AI Workspace" entry that opens/closes the panel

## Excluded

- Persisting conversation history to the database or across browser sessions
- Streaming / server-sent events for AI responses (standard request/response only)
- Auth or RBAC (existing localhost trust model is unchanged)
- Changes to the Supervisor service (`services/supervisor/main.py`)
- Modifications to any existing ticket, daemon, approval, or workflow route
- Voice input, file attachments, or image rendering in the workspace
- GitHub token management UI (token must already be available in the project's environment)
- Rate limiting or quota enforcement specific to the workspace endpoint

## Acceptance criteria

- Every `/projects/:projectId/*` route renders the AI workspace toggle; the panel survives navigating between Tickets, Dashboard, Logs, and other sub-pages without resetting the conversation
- Switching to a different project resets the conversation history
- `POST /projects/{project_id}/workspace/chat` returns `HTTP 200` with a non-empty `reply` field for an informational query (e.g. "How many tickets are in progress?")
- A functional development request (e.g. "Add dark mode") returns `intent: functional_dev` and a proposed GitHub issue draft; no code is written, no commit is created
- Confirming the issue creation from the panel calls `create-issue` and displays the returned `issue_url`
- An actionable request in the allowlist (e.g. "Restart the daemon") results in the corresponding Supervisor or Control API endpoint being called; the reply confirms the action was dispatched
- An action outside the allowlist (e.g. "Merge the PR") is refused with a plain-language explanation; no Supervisor endpoint is called
- The workspace panel never directly invokes Supervisor or any internal service endpoint; all calls go through the workspace route in Control API
