Now I have a complete picture of the bug. Here is the implementation plan.

---

## Objective

Fix `runtime_base_root` incorrectly resolving to `Path('/')` when `AI_DEV_FACTORY_RUNTIME_ROOT` is set to `'/'` (or any path whose `.parent` is `/`), which causes the false "workspace escape" error `project_id 'test-ai-dev' would escape the workspace directory: /test-ai-dev`. The fix must address the source of the bad resolution and add the missing guard as defense-in-depth, with full regression test coverage.

## Included

**Root-cause fix — source resolution**

- `services/supervisor/main.py` — `_runtime_base_root()` (lines 71–85): after computing `Path(factory_root).parent`, detect if the result is `Path('/')` and raise `RuntimeError("AI_DEV_FACTORY_RUNTIME_ROOT resolves to filesystem root '/' — check environment configuration")`. Same guard when `RUNTIME_BASE_ROOT` env var itself resolves to `Path('/')`.
- `services/control_api/main.py` — `create_app()` initialization (lines 70–81): after computing `_runtime_root.parent`, apply the same check and raise a `RuntimeError` before assigning `app.state.runtime_base_root`.

**Defense-in-depth guard**

- `services/control_api/services/project_id.py` — `assert_contained()` (lines 52–71): extend the existing guard block to also reject `runtime_root == Path('/')`, raising `ValueError("invalid runtime_base_root: '/' (filesystem root)")`. This covers the case where a caller bypasses the source-level check or loads a bad value from `workspace.json`.

**Regression tests**

- `tests/test_project_id.py`: add `test_assert_contained_raises_on_filesystem_root()` covering `Path('/')` → expects `ValueError`.
- `tests/test_supervisor_runtime_base_root.py` (new file, or extend nearest existing supervisor unit test): parametric test for `_runtime_base_root()` with:
  - `AI_DEV_FACTORY_RUNTIME_ROOT=/` → raises `RuntimeError`
  - `RUNTIME_BASE_ROOT=/` → raises `RuntimeError`
  - Valid env value → returns correct `Path`
  - No env → returns `Path.home() / "runtime"`
- `tests/test_control_api_main.py` (or nearest existing): test that `create_app()` raises when `AI_DEV_FACTORY_RUNTIME_ROOT=/` produces `Path('/')`.

## Excluded

- Fixing `project_registry.py` loading `Path('/')` from `workspace.json` (separate persistence concern; no live data path currently produces this).
- Refactoring `runtime_resolver.py` (uses values already validated upstream).
- Changes to the HTTP schema, supervisor bootstrap endpoint logic beyond the guard, or any other env variable handling.
- Adding `Path('/')` detection inside `bootstrap_project_host()` (covered by the source fix and `assert_contained` guard).

## Acceptance criteria

- Importing `test-ai-dev` with `AI_DEV_FACTORY_RUNTIME_ROOT=/` raises a `RuntimeError` at app startup, never producing `/test-ai-dev`.
- `assert_contained(Path('/'), 'test-ai-dev')` raises `ValueError`.
- `assert_contained(None, ...)`, `assert_contained(Path(''), ...)`, `assert_contained(Path('.'), ...)` continue to raise (no regression).
- `assert_contained(Path('/valid/runtime'), 'test-ai-dev')` returns `Path('/valid/runtime/test-ai-dev')` (happy path preserved).
- All new parametric tests for `_runtime_base_root()` pass.
- Full existing test suite passes without modification.
