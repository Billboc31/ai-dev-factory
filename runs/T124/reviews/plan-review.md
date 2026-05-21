# Plan review — T124

Decision: PLAN_FIX_REQUIRED

The plan is coherent but too large for one safe ticket.

Please reduce T124 to a V1 focused on read-only project discovery and UI selection.

V1 should include:

- project registry service
- GET /api/projects
- default ai-dev-factory project
- dashboard project selector or sidebar
- current project name visible in the UI
- tests for project discovery and /api/projects

V1 should exclude:

- remounting all routers under /projects/{project_id}
- rewriting all frontend API clients
- project-scoped daemon actions
- project-scoped ticket actions
- runtime data migration
- multi-daemon orchestration

Existing /api/daemon, /api/tickets and /api/project-map routes must stay unchanged in V1.

Follow-up ticket:
project-scoped APIs and actions can be implemented later once project discovery and UI selection are stable.
