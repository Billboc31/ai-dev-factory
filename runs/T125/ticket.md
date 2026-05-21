# T125 — T125 — Project-scoped runtime APIs and daemon isolation

**Source**: GitHub Issue #89

## Description

# Objective

Extend the multi-project foundations from T124 by making runtime APIs and runtime state fully project-scoped.

## Included

- Add project-scoped API routes for daemon, tickets and project-map.
- Add shared backend project resolution dependency.
- Resolve runtime roots per project.
- Isolate daemon state, logs, workers, queues and runtime artifacts per project.
- Add project-aware frontend API clients.
- Refresh dashboard runtime data when switching project.
- Add tests for project isolation and project-scoped runtime behavior.

## Excluded

- Multi-user authentication.
- Cross-project orchestration.
- Distributed runtimes.
- Kubernetes/container orchestration.
- SaaS billing/account management.
- Plugin architecture.
- Remote daemon execution.

## Acceptance criteria

- Runtime actions only affect the selected project.
- Logs, workers and queues are isolated per project.
- Project-scoped runtime endpoints return only project-specific data.
- Switching project refreshes dashboard runtime state correctly.
- Existing single-project workflows continue to function.
- Tests validate project isolation with multiple runtime roots.
- Runtime artifacts are no longer duplicated across unrelated worktrees or projects.
