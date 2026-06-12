# T186 — T186 - Auto-register current AI Dev Factory project as a first-class workspace project

**Source**: GitHub Issue #222

## Description

# Objective

Ensure the currently running AI Dev Factory repository is automatically managed as a normal workspace project.

The current AI Dev Factory repo must appear automatically in the workspace and behave exactly like any imported project.

There must not be a special-case UX or hidden runtime model for the main repository.

---

# Required behavior

On startup:

- detect current repository root
- derive project ID
- auto-register project if missing
- expose it in `/projects`
- allow full project workflow support

The current project must support:

- tickets
- worktrees
- logs
- daemon management
- supervisor management
- runtime paths
- dashboard pages
- sidebar navigation

exactly like imported projects.

---

# Constraints

- no hidden internal project type
- same APIs as imported projects
- same runtime model
- same routing model
- same registry model

---

# Acceptance criteria

- current AI Dev Factory repo auto-appears in `/projects`
- no manual import required
- current repo visible in sidebar
- current repo supports ticket workflows
- daemon/supervisor controls work
- imported projects still work
- no duplicate registration across restarts
