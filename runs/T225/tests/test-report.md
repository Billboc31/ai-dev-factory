---

**TEST_COMPLETE — all 6 acceptance criteria PASS.**

Here is the summary:

| Acceptance Criterion | Result |
|---|---|
| Every project has its own persistent AI workspace | **PASS** — `ProjectWorkspacePanel` is rendered for any active project, with isolated state per `projectId` |
| Workspace remains available while navigating | **PASS** — panel is mounted outside `<Routes>` in `App.jsx`, navigation never unmounts it |
| AI automatically receives the current project context | **PASS** — `_workspace_project_context()` injects daemon state, project root, and ticket titles into every AI call |
| Every action routed through the Supervisor | **PASS** — Control API is a pure proxy; Supervisor is the sole decision authority |
| Functional development requests redirected to GitHub issue creation | **PASS** — `functional_dev` intent triggers `gh issue create`, never code generation |
| Only explicitly allowed actions can be executed | **PASS** — `_WORKSPACE_CAPABILITIES` allowlist (3 capabilities), validated at proposal time and again at confirmation time |

**6/6 automated security tests pass** (unknown capability rejection, forged action_id 404, cross-project action_id 403, functional_dev isolation, empty draft 422, error message sanitization).

No regressions. No blocking issues. Report written to `runs/T225/tests/test-report.md`.
