# T184 — T184 - Auto-register current AI Dev Factory project as a first-class workspace project

**Source**: GitHub Issue #220

## Description

# Objective

Ensure the currently running AI Dev Factory repository is automatically managed as a normal workspace project.

After T181/T182, the workspace supports importing existing projects, but the current AI Dev Factory repo itself is not automatically registered and visible in the workspace.

The current project must behave exactly like any imported project.

There must not be a special-case UX where the main AI Dev Factory repository lives outside the workspace model.

---

# Required behavior

On startup:

- detect the current repository root;
- derive a project ID;
- auto-register the project if missing from the workspace registry;
- expose it in `/projects`;
- allow it to use the same project dashboard/runtime/daemon workflow as imported projects.

The current project must support:

- project dashboard
- tickets
- worktrees
- logs
- daemon management
- supervisor management
- runtime paths
- sidebar navigation

exactly like any other project.

---

# Important constraint

Do NOT create a special hidden/internal project type.

The current AI Dev Factory project must use:

- the same registry model;
- the same runtime model;
- the same UI model;
- the same APIs;
- the same project routing;

as all other projects.

---

# Backend changes

## Workspace bootstrap

At startup:

- if `workspace.json` does not exist, initialize it;
- if the current repo is missing from the workspace registry, auto-register it;
- avoid duplicate registration;
- preserve imported projects.

## Runtime compatibility

The existing runtime layout must remain compatible with the new project-centric model.

The auto-registered AI Dev Factory project must resolve valid:

- runtime root
- logs dir
- state dir
- worktrees dir
- daemon PID paths

without requiring a re-import.

---

# Frontend changes

- The current AI Dev Factory project appears automatically in the Projects page.
- It appears in the workspace sidebar.
- It can become the active selected project.
- All project pages work with it.
- It behaves identically to imported projects.

---

# Acceptance criteria

- Fresh startup automatically exposes the current AI Dev Factory repo in `/projects`
- No manual import is required for the current repo
- The current project appears in the sidebar
- The current project can open dashboard/tickets/worktrees/logs pages
- The current project supports daemon management
- Imported projects still work normally
- No duplicate registration occurs across restarts
- The current project uses the same project APIs and routing as imported projects
