Now I have enough context. Here is the implementation plan:

---

## Objective

Replace the hardcoded `<runtime_root>/projects/<project_id>` path model with a dedicated per-project runtime root computed as `<runtime_base_root>/<project_id>`, so importing a project like `/Users/pierrebocquet/test-ai-dev` creates its runtime at `~/runtime/test-ai-dev` and never touches `/runtime` or the AI Dev Factory runtime tree.

## Included

**New concept — `RUNTIME_BASE_ROOT`**
- New env var `RUNTIME_BASE_ROOT` (e.g. `~/runtime`), distinct from `AI_DEV_FACTORY_RUNTIME_ROOT`
- Default fallback: parent of `AI_DEV_FACTORY_RUNTIME_ROOT`, or `~/runtime`
- Per-project runtime root = `RUNTIME_BASE_ROOT / project_id`

**`services/supervisor/main.py`**
- Add `_runtime_base_root() -> Path` reading `RUNTIME_BASE_ROOT` env var with fallback
- Update `_project_runtime_root(project_id)` (line ~1603): replace `base / "projects" / project_id` with `_runtime_base_root() / project_id`
- Update bootstrap endpoint (line ~1542): create dirs directly under `_runtime_base_root() / project_id /` (not `body.runtime_root / "projects" / project_id /`)
- Add `clones/` to the directory creation list alongside `runs/`, `logs/`, `state/`, `worktrees/`
- Return `project_runtime_root` in the bootstrap response body

**`services/control_api/services/project_bootstrap.py`**
- Add `runtime_base_root` parameter (resolved from app state)
- Compute `project_runtime_root = runtime_base_root / project_id` before calling supervisor
- Pass `project_runtime_root` in the supervisor POST body (replace the current `runtime_root` field)
- Store `project_runtime_root` in `BootstrapResult` and persist it in `ProjectRegistry`

**`services/control_api/services/runtime_resolver.py`**
- Update all `resolve_*_dir(project_root, project_id=None)` signatures to also accept `project_runtime_root: Path | None = None`
- When `project_runtime_root` is provided, derive the directory directly from it (e.g. `project_runtime_root / "runs"`) instead of building `RUNTIME_ROOT / "projects" / project_id / "runs"`
- Remove the `RUNTIME_ROOT/projects/{project_id}` path construction branch

**`services/control_api/services/project_id.py`**
- Update `assert_contained(runtime_root, project_id)` (line ~52): check that the resolved project path stays inside `runtime_base_root`, not inside `runtime_root / "projects"`

**`services/control_api/main.py`**
- Read `RUNTIME_BASE_ROOT` env var in `create_app()` and store in `app.state.runtime_base_root`
- Pass `runtime_base_root` to `bootstrap()` and `auto_bootstrap()`

**`services/control_api/routes/projects.py`**
- Pass `app.state.runtime_base_root` to `bootstrap()` (replacing `app.state.runtime_root` for the per-project path calculation)

**`deploy/.env.example`**
- Add `RUNTIME_BASE_ROOT=/Users/<you>/runtime`

**`ProjectRegistry` / `BootstrapResult` models** (whichever file defines them)
- Add `project_runtime_root: Path` field to `BootstrapResult`
- Persist `project_runtime_root` per registered project so daemon routes can retrieve it without recomputing

**Tests**
- Update existing bootstrap unit tests to assert paths use `runtime_base_root / project_id` not `runtime_root / "projects" / project_id`
- Add a test: importing a project whose `project_id` equals `ai-dev-factory` produces a runtime root that is sibling to, not nested inside, the AI Dev Factory runtime root

## Excluded

- Changes to the Traefik / infra routing layer (`infra_service_manager.py`) — it manages host-global infra, not per-project runtimes
- Migrating existing already-bootstrapped projects (no migration script)
- UI or frontend changes
- Changes to how `project_id` is normalized or validated beyond the `assert_contained` fix
- Docker Compose volume mounts (the `HOST_RUNTIME_ROOT` / `CONTAINER_RUNTIME_ROOT` mapping for the AI Dev Factory container itself is unaffected)

## Acceptance criteria

- `POST /projects/import` with `{"project_path": "/Users/pierrebocquet/test-ai-dev"}` succeeds without any `OSError`
- The created runtime directories are at `$RUNTIME_BASE_ROOT/test-ai-dev/{clones,worktrees,runs,state,logs}/` — not under `/runtime/projects/…`
- `$AI_DEV_FACTORY_RUNTIME_ROOT` (e.g. `~/runtime/ai-dev-factory`) remains isolated: no subdirectory named `projects/` is created inside it for imported projects
- Two distinct projects can be imported; each gets an independent sibling directory under `RUNTIME_BASE_ROOT`
- No code path writes to `/runtime/projects/…`
- All existing bootstrap unit tests pass
- The new `assert_contained` check rejects a `project_id` that would escape `RUNTIME_BASE_ROOT`
