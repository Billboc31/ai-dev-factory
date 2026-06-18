# T193 — T193 - Make ticket boards, runs, logs and daemon lifecycle fully project-scoped

**Source**: GitHub Issue #237

## Description

# Objective

Now that project import/bootstrap works, the UI still shows the same ticket board as the ai-dev-factory project when selecting another managed project.

This indicates that ticket/runs/log/daemon data is still being read from the global ai-dev-factory runtime instead of the selected project's runtime.

---

# Current problem

Example:

Project A:

```text
ai-dev-factory
```

Project B:

```text
test-ai-dev
```

When opening Project B:

- ticket board shows Project A tickets
- daemon status appears shared
- runs/logs appear shared

The selected project is not acting as an isolation boundary.

---

# Expected architecture

Each project owns:

```text
project_runtime_root/
├── runs/
├── worktrees/
├── logs/
├── state/
└── daemon/
```

All ticket board information must come from the selected project's persisted:

```text
project_runtime_root
```

and never from the ai-dev-factory runtime unless that project is explicitly selected.

---

# Required changes

## Ticket board

Board queries must be project-scoped.

Routes must use:

```text
project_id
```

and resolve:

```text
project_runtime_root
```

from the project registry.

No global ticket source.

---

## Runs and logs

When viewing a project:

```text
runs/
logs/
```

must come from that project's runtime root.

Example:

```text
runtime/test-ai-dev/runs
runtime/test-ai-dev/logs
```

not:

```text
runtime/ai-dev-factory/runs
```

---

## Daemon lifecycle

Each project must have its own daemon.

Example:

```text
ai-dev-factory -> daemon A

test-ai-dev -> daemon B
```

Daemon state, PID, status and logs must be project-specific.

Starting/stopping a daemon must affect only the selected project.

---

## UI

Project selection must refresh:

- board
- tickets
- runs
- logs
- daemon status

using the selected project context.

No cached global board.

---

# Acceptance criteria

- Selecting test-ai-dev shows only test-ai-dev tickets.
- Selecting ai-dev-factory shows only ai-dev-factory tickets.
- Runs/logs are isolated per project.
- Each project has an independent daemon lifecycle.
- No fallback to the ai-dev-factory runtime when another project is selected.
- Switching projects refreshes the UI correctly.
