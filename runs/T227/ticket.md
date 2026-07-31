# T227 — Add pull and local backend/frontend redeployment action to AI Workspace chat

**Source**: GitHub Issue #311

## Description

## Objective

Allow the integrated AI Workspace chat to pull the latest code and redeploy the current project’s local backend and/or frontend from a natural-language request.

## User story

As a user accessing AI Dev Factory remotely, I want to tell the integrated Claude chat:

> Pull the latest changes and redeploy the backend and frontend of this project.

so that I can update the locally hosted test environment without connecting manually to the host machine.

## Expected interaction

Example request:

> Pull and redeploy the backend and frontend of Timizer.

The Workspace must:

1. resolve the current or explicitly named project;
2. resolve the configured repository, branch, backend service, and frontend service;
3. prepare a structured redeployment action;
4. show the exact target and operation for human confirmation;
5. delegate the approved action to the Supervisor;
6. pull the configured branch;
7. rebuild and restart the requested local components;
8. return execution status and useful logs to the conversation.

## Structured action

The LLM should produce a constrained action proposal similar to:

```json
{
  "action": "redeploy_project",
  "project_id": "timizer",
  "pull": true,
  "branch": "main",
  "components": ["backend", "frontend"]
}
```

The frontend must never provide arbitrary working directories, shell commands, or internal service endpoints.

## Project configuration

Each authorized project must define its local redeployment recipe outside the prompt, for example:

```yaml
projects:
  timizer:
    repository_path: /projects/timizer
    default_branch: main
    redeploy:
      backend:
        service: backend
      frontend:
        service: frontend
```

The implementation may translate these entries into the repository’s existing Docker Compose or approved deployment commands.

## Requirements

- Support natural-language requests targeting:
  - backend only;
  - frontend only;
  - backend and frontend.
- Use the active Workspace project when the request says “this project”.
- Allow an explicit project name only when it resolves to an authorized configured project.
- Use only server-side project configuration and allowlisted operations.
- Route every action through the Supervisor.
- Require human confirmation before running the pull or redeployment.
- The confirmation card must display:
  - project;
  - repository path or safe project identifier;
  - branch;
  - whether a pull will occur;
  - components to rebuild/restart;
  - whether local uncommitted changes were detected.
- Refuse execution when:
  - the project is unknown or not authorized;
  - no redeployment recipe exists;
  - the branch is not allowed;
  - the repository has unsafe local changes according to the configured policy;
  - another deployment for the same project is already running.
- Do not use an unrestricted LLM-generated shell command.
- Stream or periodically return progress for pull, build, restart, and health verification.
- Return concise success or failure output with useful log excerpts.
- Record the request, confirmation, resolved action, executor result, and actor in the audit trail.
- Keep the operation local to the AI Dev Factory host; production deployment is out of scope.

## Suggested execution states

- `PROPOSED`
- `AWAITING_CONFIRMATION`
- `PULLING`
- `BUILDING`
- `RESTARTING`
- `VERIFYING`
- `SUCCEEDED`
- `FAILED`

## Acceptance criteria

- From a project Workspace, “pull and redeploy this project” resolves to that project.
- The user can request backend only, frontend only, or both.
- No repository mutation or service restart occurs before confirmation.
- The Supervisor executes only the configured redeployment recipe.
- The selected branch is pulled using the configured safe strategy.
- Backend and frontend services are rebuilt/restarted according to the requested components.
- Concurrent redeployment of the same project is prevented.
- Pull, build, restart, and health-check progress is visible from the chat.
- Success returns the deployed revision and local/preview URL when configured.
- Failure returns the failed stage and actionable log excerpts.
- Arbitrary shell commands, paths, branches, and endpoints supplied by the model or frontend are rejected.
- Existing Workspace conversations and non-mutating chat behavior continue to work.

## Out of scope

- Production or cloud deployment.
- Arbitrary remote shell access.
- Allowing the LLM to compose unrestricted commands.
- Rollback management.
- Multi-host deployment orchestration.
