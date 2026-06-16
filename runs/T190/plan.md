The revised plan is written to `runs/T190/plan.md`. Here it is:

---

## Objective

Fix the supervisor's project bootstrap to resolve the runtime base from its own environment variables (`RUNTIME_BASE_ROOT` → parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `~/runtime`), discard the untrusted `runtime_root` field from the Control API request body, and persist the computed `project_runtime_root` in the project registry so that all subsequent operations (worktrees, runs, logs, daemons) use the persisted value rather than recomputing it from environment variables.

## Included

**`services/supervisor/main.py`**
- Add `_runtime_base_root() -> Path` resolving in this order: `RUNTIME_BASE_ROOT` → parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `Path.home() / "runtime"`. Never `/runtime`.
- Rewrite `bootstrap_project_host`: call `_runtime_base_root()`, ignore `body.runtime_root`, compute `project_runtime_root = runtime_base_root / project_id`, log all four fields before `mkdir`, return 422 if not writable, create `{clones,worktrees,runs,state,logs}`, return `str(project_runtime_root)` as `runtime_root`.

**`services/control_api/services/project_registry.py`**
- Add `project_runtime_root: Path | None = None` to `ProjectEntry`.
- Update `_persist()`, `load_from_workspace_file()`, `register()`, `ensure_registered()` to carry the new field.
- Add `resolve_runtime_root(project_id) -> Path | None` accessor.

**`services/control_api/services/project_bootstrap.py`**
- In `bootstrap()` and `auto_bootstrap()`: pass `project_runtime_root=Path(data["runtime_root"])` to the registry calls.

**`services/control_api/services/runtime_resolver.py`**
- Add optional `project_runtime_root` param to all four `resolve_*_dir` functions; when provided, return `project_runtime_root / <subdir>` directly. Remove `/projects/` from the fallback computation.

**`services/control_api/services/project_id.py`**
- Remove the hardcoded `/projects/` segment from `assert_contained()`.

**Routes (`daemon.py`, `tickets.py`)**
- Look up `registry.resolve_runtime_root(project_id)` and pass it to resolver calls.

**Tests**: `test_project_id.py`, `test_project_bootstrap.py`, `test_project_registry.py` — updated and new assertions for the path layout change and persistence round-trip.

## Excluded

- Removing `runtime_root` from `ProjectBootstrapHostRequest`; changes to `path_mapper.py`; actual git clone creation; env documentation; `runtime_dashboard.py` sandbox functions.

## Acceptance criteria

- Bootstrap creates `/Users/pierrebocquet/runtime/test-ai-dev/{clones,...}`, not `/runtime/projects/...`.
- `_runtime_base_root()` resolves correctly for both env-var scenarios.
- HTTP 422 returned when base root is not writable — no unhandled `OSError`.
- Bootstrap log shows all four path fields before `mkdir`.
- `registry.resolve_runtime_root("test-ai-dev")` returns the persisted value after bootstrap.
- `workspace.json` persists `project_runtime_root`; API restart preserves it.
- Worktree/run/log/daemon resolvers use the persisted value — no recomputation.
- All updated and new tests pass.
- Existing `ai-dev-factory` runtime is untouched.
