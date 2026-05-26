# T148 — T148 — Generic sandbox undeploy lifecycle

**Source**: GitHub Issue #143

## Description

Goal: introduce a generic undeploy and cleanup lifecycle for sandbox runtimes.

Context:
Sandbox deletion currently removes files and state, but running services may continue to exist after cleanup.

Observed behavior:
- sandbox web/API containers may continue running after sandbox deletion
- docker compose projects may remain active
- runtime processes may survive cleanup
- cleanup behavior is partially hardcoded
- after deleting a sandbox, creating a new sandbox may incorrectly return `already running`
- stale pid files, locks or runtime metadata may survive cleanup

The system now needs a generic undeploy lifecycle.

Scope:
- introduce a generic undeploy lifecycle model
- allow projects to define undeploy and cleanup steps
- sandbox cleanup must execute undeploy lifecycle before removing files
- support stopping docker compose projects when applicable
- support generic stop scripts
- support runtime cleanup hooks
- no hardcoded docker-only assumptions in the orchestrator
- cleanup must stop runtime processes before removing sandbox directories
- cleanup must safely release ports, runtime state and worktrees
- cleanup must remove stale pid files and stale locks
- cleanup must clear sandbox runtime registry/state entries
- undeploy lifecycle must remain generic and project-agnostic

Potential future deploy.yml direction:
- deploy steps
- undeploy steps
- cleanup hooks
- runtime shutdown strategies

Tests:
- compose project cleanup
- stop script execution
- runtime process cleanup
- worktree cleanup
- cleanup safety
- repeated cleanup idempotency
- stale pid cleanup
- stale lock cleanup
- recreate sandbox after cleanup

Out of scope:
- AI auto-fix loops
- cloud deployment
- distributed orchestration

Acceptance:
- deleting a sandbox stops its runtime services before removing files
- no orphan compose projects remain after cleanup
- runtime processes are terminated safely
- ports are released after cleanup
- stale runtime state is removed during cleanup
- creating a new sandbox after deletion never incorrectly returns `already running`
- cleanup is idempotent
- cleanup remains generic and project-agnostic
