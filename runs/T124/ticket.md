# T124 — T124 — Multi-project runtime boards and project isolation

**Source**: GitHub Issue #87

## Description

# Objective

Introduce first-class multi-project support in the dashboard and runtime architecture so multiple independent AI-managed projects can be orchestrated from a single control surface.

## Included

- Add a project abstraction to the runtime model.
- Introduce project-aware runtime roots and worktree isolation.
- Add a project selector/sidebar in the dashboard.
- Display separate boards per project.
- Separate:
  - tickets
  - runtime state
  - daemon status
  - workers
  - logs
  - queue/intake
  - runtime artifacts
- Add backend APIs/services for project discovery and project-scoped runtime operations.
- Add frontend routing/state for project-aware navigation.
- Support the existing `ai-dev-factory` project as the initial/default project.
- Add tests for project isolation and project-scoped runtime queries.

## Excluded

- Multi-user authentication.
- Cross-project orchestration.
- Distributed remote runtimes.
- Kubernetes/container orchestration.
- SaaS billing/account management.
- Full plugin architecture.

## Acceptance criteria

- Dashboard can display multiple independent projects.
- Each project has isolated runtime state and worktrees.
- Switching project updates the visible board/runtime context.
- Runtime actions only affect the selected project.
- Existing `ai-dev-factory` workflows continue to function.
- Project-scoped runtime APIs are covered by tests.
- Runtime garbage files are not shared across project runtimes.
