# T181 — T181 - Add existing project bootstrap and per-project agent runtime management

**Source**: GitHub Issue #215

## Description

# Objective

Transform AI Dev Factory from an environment-centric tool into a multi-project workspace capable of bootstrapping existing projects and managing isolated per-project agent runtimes.

The immediate focus is NOT deployment.

The focus is:
- project bootstrap
- project management UI
- ticket/dev workflow
- per-project supervisor/daemon isolation

Deployment/runtime sandbox orchestration can come later.

---

# MVP Scope

## 1. Multi-project workspace UI

Add a true project-centric UI.

Required:

- Projects home/dashboard
- Sidebar project navigation
- Open existing project
- Import existing project
- Create new project (placeholder flow acceptable initially)
- Per-project dashboard

Each project should expose:

- tickets/issues
- branches/worktrees
- agents
- logs
- runtime state
- settings

---

# 2. Existing project bootstrap

Add a bootstrap flow for existing repositories/projects.

Flow:

```text
Import existing project
→ choose local repo/folder
→ detect stack
→ generate ai-dev-factory metadata/config
→ initialize project runtime structure
→ enable ticket/agent workflow
```

Required bootstrap outputs:

- project config
- runtime directory structure
- worktrees directory
- logs/state directories
- minimal supervisor metadata
- project registration in workspace

Out of scope initially:

- Traefik
- deploy environments
- healthchecks
- production runtime deployment

---

# 3. Per-project agent runtime isolation

Each project must have isolated:

- supervisor
- daemon
- worktrees
- logs
- state
- PID files
- locks

No project may reuse another project's runtime directories.

Required:

```text
1 supervisor per project
1 daemon per project
```

with runtime roots derived from the project.

Example:

```text
projects/
  personal-rag/
    runtime/
      logs/
      state/
      worktrees/
```

---

# 4. Ticket/dev workflow

The imported project must immediately support:

- issue creation
- branch creation
- ticket/TXXX-* naming
- worktree creation
- Claude/Coder execution
- commit/push/PR workflow

without requiring deployment support.

---

# Important architecture goal

Move from:

```text
Environment-centric architecture
```

to:

```text
Project-centric architecture
```

Environments should eventually become derived runtime instances of a project, not the primary top-level entity.

---

# Acceptance criteria

- Workspace supports multiple projects
- Existing local projects can be imported
- Imported projects appear in the UI
- Imported projects get isolated runtime directories
- Each project can run its own supervisor and daemon
- Ticket/dev workflow works for imported projects
- Worktrees/logs/state are isolated per project
- No deployment/Traefik dependency is required for the MVP
