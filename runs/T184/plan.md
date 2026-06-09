Now I have enough context to write the plan.

## Objective

Auto-register the current AI Dev Factory repository into the workspace registry at backend startup, so it appears in `/projects` and behaves identically to any manually imported project — no manual import required, no special-case code path.

## Included

**Backend — `services/control_api/services/project_bootstrap.py`**

- Add a new function `auto_register_if_missing(registry, project_root, runtime_root)` that:
  - Iterates all currently registered projects and short-circuits if `project_root` is already present (duplicate guard keyed on root path, not just project_id).
  - Derives a `project_id` by reading the `name` field from `.ai-dev-factory/project.yml` if present; otherwise sanitizes `project_root.name` (basename lowercased, non-alphanumeric chars replaced with `-`) to match the existing validation regex.
  - Calls the existing `bootstrap()` function with the derived id and root, which handles: runtime dir creation, stack detection, writing `project.yml` if absent, and calling `registry.register()`.

**Backend — `services/control_api/main.py`**

- After the `ProjectRegistry` is initialized in workspace-file mode (i.e., `runtime_root` is set and `load_from_workspace_file()` is used), call `auto_register_if_missing(registry, project_root, runtime_root)`.
- No change to single-root mode or projects-root scan mode.

**No frontend changes.** The current project becomes visible in the sidebar and all project pages automatically once it is registered in the workspace, because the existing `/projects` API and frontend routing treat all registry entries identically.

## Excluded

- Changes to `ProjectRegistry` internals (the existing `register()` and `resolve()` are sufficient).
- Changes to single-root mode or projects-root scan mode startup paths.
- Changes to the `/projects/import` endpoint or bootstrap validation logic.
- Any new project type, flag, or schema field distinguishing the auto-registered project from imported ones.
- Frontend routing or sidebar changes.
- Handling the case where `AI_DEV_FACTORY_RUNTIME_ROOT` is not set (single-root mode is unchanged).

## Acceptance criteria

- On fresh startup with `AI_DEV_FACTORY_RUNTIME_ROOT` set and an empty or absent `workspace.json`, `GET /projects` returns at least one project whose `root` equals the current repository root.
- Restarting the server does not produce a duplicate entry in `workspace.json` for the current repo.
- A project imported manually before startup is still present after startup (no regressions to existing registry entries).
- The auto-registered project's `project_id` appears in all project-scoped API routes (`/projects/{project_id}/dashboard`, `/projects/{project_id}/tickets`, `/projects/{project_id}/daemon/status`, etc.) and returns valid responses.
- The auto-registered project appears in the workspace sidebar alongside any other imported projects.
- `workspace.json` after auto-registration contains only one entry for the current repo root, regardless of how many times the server has been restarted.
