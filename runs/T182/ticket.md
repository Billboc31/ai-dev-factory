# T182 — T182 - Add full multi-project workspace UI and project dashboards

**Source**: GitHub Issue #217

## Description

# Objective

Build the real multi-project workspace UI on top of the T181 backend/project-bootstrap foundation.

T181 introduces the backend runtime/project isolation and a minimal import UI.

T182 must introduce the actual project-centric UX:

- workspace sidebar
- project switcher
- per-project dashboards
- daemon/supervisor controls
- ticket/worktree visibility
- logs/runtime visibility

The goal is to move AI Dev Factory away from a single-project environment-centric UI into a true multi-project software factory workspace.

---

# Scope

## 1. Workspace shell

Add a persistent workspace shell/layout.

Required:

- left sidebar
- active project selection
- project switcher
- project quick actions
- global workspace header

Sidebar should expose:

- Projects
- Active project
- Tickets
- Worktrees
- Agents
- Logs
- Runtime
- Settings

---

# 2. Projects dashboard

Add a real project dashboard page.

Each project dashboard must display:

- project name
- detected stack
- project root
- runtime root
- daemon state
- supervisor state
- number of active tickets
- number of active worktrees
- recent activity

Add project actions:

- Start daemon
- Stop daemon
- Open logs
- Open tickets
- Open worktrees
- Re-import/rescan project

---

# 3. Per-project runtime status cards

Add runtime cards/components for:

- supervisor
- daemon
- runtime paths
- logs paths
- PID state
- active workers

The UI must clearly distinguish:

- global runtime
- project runtime
- project daemon

to avoid the confusion seen in previous deploy/runtime debugging.

---

# 4. Tickets/worktrees visibility

Add per-project views for:

- tickets
- ticket states
- branches
- worktrees
- active agent runs

The user must immediately understand:

- which tickets belong to which project
- which daemon is managing which worktree
- which worktrees are active

---

# 5. Logs visibility

Add project-level logs views.

Required:

- daemon logs
- supervisor logs
- recent runtime events
- runtime paths visibility
- quick copy/open actions

Do not require shell access for basic runtime inspection.

---

# 6. Routing and project context

Add project-aware routing.

Preferred direction:

```text
/projects/:projectId/*
```

Examples:

```text
/projects/personal-rag/dashboard
/projects/personal-rag/tickets
/projects/personal-rag/worktrees
/projects/personal-rag/logs
```

The active project context must survive navigation and refresh.

---

# Important constraints

- Do NOT reintroduce deployment complexity.
- Do NOT depend on Traefik or sandbox deploys.
- Focus on the software-factory workflow.
- The UI must remain lightweight and developer-focused.

---

# Acceptance criteria

- Workspace sidebar exists
- Multiple projects can be navigated from the UI
- Active project context is visible everywhere
- Project dashboards display runtime and daemon state
- Per-project ticket/worktree views exist
- Logs can be inspected from the UI
- Daemon start/stop works from the UI
- The user can clearly distinguish project runtimes from the global runtime
- Refresh/navigation preserves project context
