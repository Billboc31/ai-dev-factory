## Objective

Add a persistent AI workspace panel to every project page, similar to Cursor's chat experience, while preserving AI Dev Factory's issue-driven development workflow.

The workspace is only a conversational user interface. **Every request, including informational queries and requested actions, must be routed through the Supervisor.** The workspace and Control API must never classify, execute, or dispatch project actions independently.

The Supervisor is responsible for:

- understanding the user request;
- loading the required live project context;
- classifying the request as `informational | actionable | functional_dev`;
- selecting the configured AI provider/model;
- enforcing the explicit workspace capability allowlist;
- requesting confirmation before mutating actions;
- executing authorized platform capabilities;
- redirecting functional development requests to GitHub issue creation.

## Architecture

```text
ProjectWorkspacePanel
        |
        v
Control API workspace route
        |
        v
Supervisor workspace endpoint
        |
        +--> project context readers
        +--> configured AI provider
        +--> authorized platform capabilities
        +--> GitHub issue creation
```

Rules:

- The frontend only calls the Control API workspace routes.
- The Control API acts as an authenticated transport/proxy and delegates every request to the Supervisor.
- The Control API does not call Claude or another model directly.
- The Control API does not classify intent and does not invoke ticket, daemon, deployment, GitHub, or workflow services directly.
- Only the Supervisor may decide and execute workspace capabilities.
- Functional development must always remain issue-driven; the workspace never writes business code, creates implementation commits, or bypasses the GitHub Issue -> AI Dev Factory workflow.

## Included

### Supervisor — `services/supervisor/routes/workspace.py` (new file, or equivalent route integrated into the existing Supervisor API)

- `POST /workspace/projects/{project_id}/chat`
  - accepts `{ message: str, conversation_history: list }`;
  - loads project context such as project metadata, GitHub repository, ticket summaries, execution state, logs, tests and deployments as required by the request;
  - invokes the configured AI provider through the existing AI/provider abstraction rather than referencing Claude directly;
  - classifies the request as `informational | actionable | functional_dev`;
  - returns a structured response such as:

```json
{
  "reply": "...",
  "intent": "informational | actionable | functional_dev",
  "proposed_action": null,
  "issue_draft": null,
  "confirmation_required": false
}
```

- Informational requests are answered using live project data available to the Supervisor.
- Functional development and bug-fix requests return a proposed GitHub issue draft containing a title and body; no code, commit or pull request is created.
- Actionable requests are resolved against an explicit Supervisor-owned allowlist.
- Initial allowed actions:
  - restart daemon;
  - rerun ticket intelligence;
  - rerun dependency analysis;
  - resume ticket execution;
  - trigger project deployment.
- Requests outside the allowlist are refused with a plain-language explanation.
- Mutating actions return a proposed action and require explicit user confirmation before execution.

### Supervisor — action confirmation endpoint

- `POST /workspace/projects/{project_id}/actions/confirm`
  - accepts a Supervisor-issued action identifier or signed action payload;
  - validates that the action was proposed for the same project and conversation/user context;
  - rechecks the capability allowlist and current project state;
  - invokes the corresponding existing Supervisor/platform capability;
  - returns the execution result.

The client must not be able to submit arbitrary internal endpoint names or tool arguments. Confirmation must refer to an action previously proposed and validated by the Supervisor.

### Supervisor — GitHub issue confirmation endpoint

- `POST /workspace/projects/{project_id}/issues/confirm`
  - accepts a Supervisor-issued issue draft identifier or validated draft payload;
  - creates the issue in the project's configured GitHub repository through the Supervisor's GitHub capability;
  - returns `{ issue_url, issue_number }`.

Issue creation is considered a mutating action and therefore requires explicit user confirmation.

### Supervisor — capability policy

- Introduce a central workspace capability registry/allowlist owned by the Supervisor.
- Each capability defines:
  - a stable capability key;
  - whether confirmation is required;
  - input validation;
  - authorization/policy checks;
  - the existing service or Supervisor handler to invoke;
  - a user-facing description.
- Unknown capabilities are denied by default.
- The AI model may propose only capability keys exposed to it by the Supervisor; it must never invent raw internal URLs or service calls.

### Control API — `services/control_api/routes/workspace.py` (new file)

- `POST /projects/{project_id}/workspace/chat`
  - validates the transport-level request shape;
  - forwards the request to the Supervisor workspace chat endpoint;
  - returns the Supervisor response unchanged or through a thin API DTO mapping.

- `POST /projects/{project_id}/workspace/actions/confirm`
  - forwards confirmation to the Supervisor action confirmation endpoint.

- `POST /projects/{project_id}/workspace/issues/confirm`
  - forwards issue confirmation to the Supervisor issue confirmation endpoint.

The Control API workspace router must not:

- invoke an AI provider directly;
- classify the request;
- maintain its own action allowlist;
- call GitHub directly;
- invoke daemon, ticket, dependency, execution or deployment routes directly.

### Control API — `services/control_api/main.py`

- Import and register the `workspace` router.

### Frontend — `apps/dashboard/src/api/workspace.js` (new file)

- `postWorkspaceMessage(projectId, message, history)` calls `/projects/{projectId}/workspace/chat`.
- `confirmWorkspaceAction(projectId, proposedAction)` calls `/projects/{projectId}/workspace/actions/confirm`.
- `confirmWorkspaceIssue(projectId, issueDraft)` calls `/projects/{projectId}/workspace/issues/confirm`.

### Frontend — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx` (new file)

- Collapsible side panel, rendered outside `<Routes>` in `AppLayout` so it survives navigation.
- Scrollable message history containing user and AI turns.
- Text input and submit button with loading and error states.
- Conversation history stored in component state and keyed by `projectId`; it resets when switching project.
- For `functional_dev`, display a GitHub issue confirmation card showing the Supervisor-proposed title and body.
- For actionable requests, display a confirmation card describing the exact Supervisor-proposed action.
- The frontend must never construct internal tool arguments or select platform endpoints itself.
- Confirmation buttons only send the opaque/validated proposal returned by the Supervisor.

### Frontend — `apps/dashboard/src/App.jsx`

- Render `<ProjectWorkspacePanel projectId={activeProject} />` in `AppLayout` alongside `<main>`, only when `activeProject` is set.

### Frontend — `apps/dashboard/src/components/ProjectSidebar.jsx`

- Add a toggle button or `AI Workspace` entry that opens and closes the panel.

## Excluded

- Persisting conversation history to the database or across browser sessions.
- Streaming or server-sent events for AI responses; standard request/response only.
- Voice input, file attachments or image rendering.
- GitHub token-management UI; credentials must already be configured for the project/platform.
- Direct source-code editing from the workspace.
- Automatic commits or pull requests for functional changes.
- New development workflows that bypass GitHub issues.
- Arbitrary tool execution or unrestricted Supervisor access.
- Workspace-specific rate limiting or quota enforcement in this first iteration.
- New RBAC design; existing authentication/authorization rules remain in force, but Supervisor policy checks must still be applied before each capability execution.

## Security and behavior constraints

- Deny by default: only explicitly registered Supervisor workspace capabilities may run.
- Every mutating action requires explicit confirmation in the UI.
- The Supervisor must revalidate a confirmed action immediately before execution.
- Project IDs, issue drafts and action proposals must be validated server-side; client-provided values are never trusted as authorization.
- Logs must identify that an action originated from the AI workspace and include the project, capability key and outcome.
- Sensitive credentials, raw tokens and secrets must never be included in AI prompts or responses.
- The AI workspace may read only project information already available to the authenticated user and Supervisor.

## Tests

### Supervisor tests

- Informational requests are classified and answered using project context.
- Functional-development requests return an issue draft and never invoke code-writing, commit or pull-request capabilities.
- Allowed actionable requests return a confirmation-required proposal without executing immediately.
- Confirming a valid proposed action invokes the expected capability once.
- Unknown or non-allowlisted actions are refused.
- Forged, expired, mismatched-project or altered action proposals are rejected.
- The configured AI provider abstraction is used; the workspace implementation does not depend directly on Claude.
- GitHub issue creation occurs only after confirmation.

### Control API tests

- Workspace routes forward requests to the Supervisor.
- No Control API workspace handler invokes AI providers, GitHub or internal operational routes directly.
- Supervisor errors and validation failures are mapped consistently to API responses.

### Frontend tests

- The panel remains mounted while navigating between pages of the same project.
- Switching projects resets the conversation.
- Functional-development responses show an issue confirmation card.
- Actionable responses show an action confirmation card.
- No mutating request is sent before explicit confirmation.
- Confirmed actions and issues display their returned result or error.

## Acceptance criteria

- Every `/projects/:projectId/*` route renders the AI workspace toggle.
- The panel survives navigation between Tickets, Dashboard, Logs and other sub-pages without resetting the conversation.
- Switching to another project resets the conversation history.
- Every workspace request follows this path: frontend -> Control API workspace route -> Supervisor.
- Neither the frontend nor the Control API directly calls an AI provider or an internal platform capability.
- An informational query such as `How many tickets are in progress?` returns `HTTP 200` with a non-empty reply based on live project data.
- A functional-development request such as `Add dark mode` returns `intent: functional_dev` and a proposed GitHub issue draft; no code, commit or pull request is created.
- The issue is created only after the user confirms the Supervisor-proposed draft.
- An allowlisted action such as `Restart the daemon` first returns a confirmation-required proposed action and is executed only after confirmation.
- The confirmed action is executed by the Supervisor through the existing platform capability.
- An action outside the allowlist such as `Merge the PR` is refused; no internal service is invoked.
- The workspace cannot submit arbitrary tools, internal URLs or execution arguments.
- All workspace-originated actions are auditable in logs.
