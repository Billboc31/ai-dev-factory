I have enough context now. Here is the plan:

---

## Objective

Add a startup hook to `create_app()` that detects the current AI Dev Factory repository root, derives its project ID, and auto-registers it via the existing `bootstrap()` machinery — so the project appears in `/projects` on first boot without a manual import.

## Included

### `services/control_api/main.py`

Add a `_self_register_current_project(runtime_root: Path, registry: ProjectRegistry) -> None` helper function that:

1. Resolves the self-project root from `AI_DEV_FACTORY_PROJECT_ROOT` env var (already used), or falls back to `_resolve_default_project_root()`.
2. Verifies the path contains a `.git` directory; logs a warning and returns early if not.
3. Derives a project ID with `normalize_project_id(project_root.name)` (from `services/project_id.py`).
4. Calls `registry.resolve(project_id)` — if not `None`, the project is already registered; log and return (idempotent).
5. Calls `bootstrap(project_root, project_id, runtime_root, registry)` to create the per-project runtime tree, write `.ai-dev-factory/project.yml`, and persist the entry to `workspace.json`.
6. Wraps the whole body in a broad `except Exception` that logs a warning and does not crash startup.

Call `_self_register_current_project(_runtime_root, app.state.project_registry)` at the end of the `load_from_workspace_file` code path in `create_app()` — that is, immediately after line 85 (`app.state.project_registry = ProjectRegistry.load_from_workspace_file(_runtime_root)`). No call is added in the `projects_root` scan path or the `from_single_root` path (not needed there).

### No other backend files require changes

- `project_bootstrap.py`: `bootstrap()` already handles directory creation, `project.yml` writing, and registry persistence — no modifications needed.
- `project_registry.py`: `resolve()` + `register()` + `_persist()` already work correctly.

### No frontend changes required

The Projects page (`ProjectsPage.jsx`), sidebar (`ProjectSidebar.jsx`), and all project sub-pages already render any entry returned by `GET /projects` uniformly. Once the backend auto-registers the project, it appears automatically.

## Excluded

- Detecting or auto-importing other git repositories found on the filesystem.
- Changes to the project data model, `workspace.json` schema, or runtime directory layout.
- A new env var to override the derived project ID (normalized basename is sufficient).
- Auto-registration in the `projects_root` scan mode or the `from_single_root` mode (these paths already expose the project correctly).
- Any frontend changes.
- Changes to the import workflow for other projects.

## Acceptance criteria

- With `AI_DEV_FACTORY_RUNTIME_ROOT` set and no pre-existing `workspace.json`, a fresh API startup results in `GET /projects` returning at least one entry whose `root` matches the current AI Dev Factory repo path.
- A second startup does not duplicate the entry in `workspace.json` and does not log a `ValueError`.
- Projects previously imported (already in `workspace.json`) still appear correctly alongside the auto-registered project.
- The auto-registered project's dashboard, tickets, worktrees, logs, and daemon pages all function (they use the same project routing as imported projects).
- If `AI_DEV_FACTORY_PROJECT_ROOT` points to a path without `.git`, the API starts normally with a warning log and no panic.
- `workspace.json` on disk after startup contains a valid entry for the self-project with the correct `root` value.
