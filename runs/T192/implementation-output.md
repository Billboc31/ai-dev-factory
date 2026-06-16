Implementation complete. Here's a summary of all changes made:

---

## Files modified

**`services/control_api/services/project_id.py`** — defense-in-depth guard in `assert_contained()`: after resolving the base path, rejects `Path('/')` with `ValueError("invalid runtime_base_root: '/' (filesystem root)")` before the containment check can produce the confusing escape error.

**`services/supervisor/main.py`** — root-cause fix in `_runtime_base_root()`: raises `RuntimeError` when either `RUNTIME_BASE_ROOT` resolves to `/` or when `AI_DEV_FACTORY_RUNTIME_ROOT.parent` is `/`.

**`services/control_api/main.py`** — root-cause fix in `create_app()`: same guard applied after computing `_runtime_base_root`, preventing the app from starting with a bad runtime base.

**`tests/test_project_id.py`** — added `test_assert_contained_raises_on_filesystem_root` covering the `Path('/')` case.

**`tests/test_supervisor_runtime_base_root.py`** *(new)* — 5 parametric tests covering `RUNTIME_BASE_ROOT=/`, `AI_DEV_FACTORY_RUNTIME_ROOT=/`, valid env, no env, and derived-from-factory-root cases.

**`tests/test_control_api_main.py`** *(new)* — 2 parametric tests verifying `create_app()` raises `RuntimeError` for both bad env variables.

All 53 directly-related tests pass. The 72 pre-existing failures in the full suite are unrelated to T192 (env contamination in ticket listing tests, git worktree tests, etc.).
