# Plan fix request — T124

The original plan is too large for one safe ticket.

Rewrite T124 as a smaller V1.

## V1 objective

Introduce read-only project discovery and a dashboard project selector while keeping existing single-project runtime APIs unchanged.

## Include in V1

- Add project registry service.
- Add GET /api/projects.
- Support existing ai-dev-factory as the default project.
- Add dashboard project selector/sidebar.
- Display current selected project in the UI.
- Keep existing /api/daemon, /api/tickets and /api/project-map routes unchanged.
- Add tests for project discovery and /api/projects.
- Add minimal frontend test for project selector if practical.

## Exclude from V1

- Do not remount all routers under /projects/{project_id}.
- Do not rewrite all frontend API clients.
- Do not make daemon/tickets/actions project-scoped yet.
- Do not migrate runtime data.
- Do not implement multi-daemon orchestration.

## Acceptance criteria

- Dashboard shows project selector with ai-dev-factory.
- Existing daemon/ticket actions continue to work.
- GET /api/projects returns discovered/default projects.
- Tests cover project discovery and backward compatibility.
