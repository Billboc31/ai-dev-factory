# T188 — T188 - Route all host filesystem project import and bootstrap operations through supervisor

**Source**: GitHub Issue #225

## Description

# Objective

Project import currently performs filesystem validation from the API layer.

This breaks when the API runs in Docker or another isolated runtime because local host paths (for example `/Users/...`) are not visible from the container.

All operations that interact with the host filesystem must be executed through the supervisor.

---

# Architecture rule

Control API:
- orchestration
- validation of request payloads
- persistence
- API responses

Supervisor:
- host filesystem access
- git inspection
- bootstrap operations
- runtime directory creation
- worktree management
- daemon lifecycle operations

The Control API must not directly assume access to host paths.

---

# Import flow

Current flow:

UI -> Control API -> filesystem checks

Target flow:

UI -> Control API -> Supervisor -> host validation -> Control API persistence

---

# Operations that must move to supervisor

Project import:
- path exists
- path is directory
- realpath resolution
- symlink validation
- git repository detection
- repository metadata discovery

Project bootstrap:
- project.yml creation
- runtime directory creation
- runtime initialization

Project management:
- worktree creation
- worktree cleanup
- log file access
- daemon start/stop
- supervisor-managed runtime operations

---

# Supervisor endpoints

Introduce host-oriented operations such as:

- validate project path
- inspect repository
- bootstrap project
- initialize runtime

Exact endpoint naming can be chosen during implementation.

---

# Error handling

Return explicit errors for:

- path does not exist
- path is not a directory
- repository not found
- permission denied
- invalid git repository
- runtime bootstrap failure

Errors must reflect host reality, not container visibility.

---

# Acceptance criteria

- Importing `/Users/...` projects works when Control API runs in Docker.
- Filesystem validation executes through supervisor.
- Bootstrap executes through supervisor.
- Control API no longer performs host filesystem assumptions.
- Existing imported projects continue to work.
- Multi-project workflow remains unchanged.
