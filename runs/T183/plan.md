Now I have a clear picture of the architecture. Here is the implementation plan.

---

## Objective

Auto-register the currently running AI Dev Factory repository as a first-class workspace project at startup, so it appears in `/projects`, the sidebar, and all project dashboards without any manual import step, using exactly the same registry/runtime/UI model as imported projects.

## Included

### Backend — `services/control_api/services/project_bootstrap.py`

- Add `auto_register_current_project(project_root: Path, registry: ProjectRegistry, runtime_root: Path) -> None`:
  - Scan `registry` for any entry whose root already equals `project_root` → if found, return early (idempotent, no duplicate).
  - Derive a project ID via the existing `normalize_project_id(project_root.name)` from `project_id.py`.
  - If the normalized ID is already taken by a *different* root, append a short suffix (`-0`, `-1`, …) until a free ID is found (max 10 attempts, then log a warning and abort without crashing).
  - Call the existing `bootstrap_project(project_root, project_id, runtime_root, registry)` to create runtime dirs, write `project.yml`, and register in the workspace.
  - Wrap in `try/except` — log any error but do not raise (startup must not be blocked).

### Backend — `services/control_api/main.py`

- In `create_app()`, after the Mode 2 branch (`load_from_workspace_file`), add a call to `auto_register_current_project(project_root, registry, runtime_root)` when `project_root` is set.
- No changes to Mode 1 (projects_root scan) or Mode 3 (from_single_root) — both already handle their cases.

### Tests — `services/control_api/tests/`

- Add `test_auto_register_current_project.py`:
  - **Test 1**: fresh workspace (no workspace.json) → project auto-registered, appears in `registry.list_projects(…)`.
  - **Test 2**: project already registered → second call is a no-op, no duplicate in registry.
  - **Test 3**: project root normalized ID collides with an existing different project → suffix appended, both projects coexist.
  - **Test 4**: bootstrap failure → exception is logged but `create_app()` does not raise.

### Frontend — no changes required

The `ProjectsPage.jsx` already polls `GET /api/projects` every 5 seconds and renders every entry returned. The sidebar (`ProjectSidebar.jsx`) likewise reflects the full registry. Once the backend registers the project, the frontend exposes it automatically.

## Excluded

- Changes to Mode 1 (projects_root scan) or Mode 3 (single-root mode) startup paths.
- Any UI changes — frontend already handles any registered project identically.
- Migration of legacy `runs/`, `logs/` directories for pre-existing data.
- Auto-registration for imported projects (they are registered explicitly via `/projects/import`).
- Any special casing, internal project type, or hidden registry entries.

## Acceptance criteria

- `GET /api/projects` returns the current AI Dev Factory repo on the first request after a fresh startup, with no prior import.
- The auto-registered project appears in the workspace sidebar and its dashboard, tickets, worktrees, logs, and daemon pages load without error.
- Restarting the server multiple times produces exactly one entry for the current repo in `workspace.json` (no duplicates).
- Manually imported projects still appear alongside the auto-registered project and behave normally.
- Removing `workspace.json` and restarting re-registers the current project cleanly.
- All four new unit tests pass (`pytest services/control_api/tests/test_auto_register_current_project.py`).
- The existing test suites (`test_project_scoped_routes.py`, `test_project_isolation.py`) continue to pass.
