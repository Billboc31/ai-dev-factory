I have everything I need. Here is the implementation plan:

---

## Objective

Fix the supervisor's project bootstrap so it derives the runtime base root from its own environment variables (`RUNTIME_BASE_ROOT` → parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `~/runtime`) instead of trusting the `runtime_root` field sent by the Control API, which carries a container-side path (`/runtime`) that does not exist on the host. The directory layout changes from `{runtime_root}/projects/{project_id}/…` to `{RUNTIME_BASE_ROOT}/{project_id}/…`, `clones/` is added to the bootstrapped directories, and the supervisor fails loudly with a 422 if the resolved root is not writable.

## Included

**`services/supervisor/main.py`**
- Add `_runtime_base_root() -> Path` that resolves in order:
  1. `Path(os.environ["RUNTIME_BASE_ROOT"]).expanduser().resolve()` if set
  2. `Path(os.environ["AI_DEV_FACTORY_RUNTIME_ROOT"]).expanduser().resolve().parent` if set
  3. `Path.home() / "runtime"` as the safe local fallback
- Rewrite `bootstrap_project_host` (line 1510):
  - Call `_runtime_base_root()` — do **not** use `body.runtime_root` for path computation.
  - Compute `project_runtime_root = runtime_base_root / body.project_id`.
  - Before creating directories, check if `runtime_base_root` is writable (`os.access(runtime_base_root, os.W_OK)` or a try/except on `mkdir`); if not, return a structured 422 `{"error": "runtime_base_root_not_writable", "detail": str(runtime_base_root)}` instead of crashing.
  - Create subdirs: `clones/`, `worktrees/`, `runs/`, `state/`, `logs/` (adding `clones/` to the existing four).
  - Update `logger.info` call to log `runtime_base_root=`, `project_runtime_root=`, `project_id=`, `project_root=`.
  - Update the return dict: `runtime_root` field returns `str(project_runtime_root)`.

**`services/control_api/services/project_id.py`**
- Rewrite `assert_contained(runtime_base, project_id)` (line 52): remove the hardcoded `/projects/` path segment. The containment check and returned path become `{runtime_base}/{project_id}` staying inside `{runtime_base}/` (i.e., `base_resolved = runtime_base.resolve()`, `candidate = (base_resolved / project_id).resolve()`).

**`services/control_api/services/runtime_resolver.py`**
- In `resolve_runs_dir`, `resolve_worktrees_dir`, `resolve_state_dir`, `resolve_logs_dir`: when `project_id` is given, replace `Path(runtime_root) / "projects" / project_id / <subdir>` with `Path(runtime_root) / project_id / <subdir>` (lines 21, 35, 48, 62).
- `resolve_project_runtime_root` (line 69) inherits the fix via the updated `assert_contained`.

**`tests/test_project_id.py`**
- `test_assert_contained_returns_correct_path` (line 123): update expected path from `tmp_path / "projects" / "my-project"` to `tmp_path / "my-project"`.
- `test_assert_contained_different_ids_produce_different_paths` (line 138): update `startswith` checks from `str(tmp_path / "projects")` to `str(tmp_path)`.

**`tests/test_project_bootstrap.py`**
- `_mock_bootstrap_response` (line 24): change `base = f"{runtime_root}/projects/{project_id}"` to `base = f"{runtime_root}/{project_id}"`.
- `test_bootstrap_returns_paths_from_supervisor` (line 59) and `test_bootstrap_runtime_dirs_are_under_project_runtime_root` (line 66): update `expected_base` / `expected_prefix` from `runtime_root / "projects" / "my-project"` to `runtime_root / "my-project"`.

## Excluded

- Removing the `runtime_root` field from `ProjectBootstrapHostRequest` (kept for API compatibility; the field is accepted but no longer used for path computation).
- Changes to `services/supervisor/path_mapper.py` (path-mapping layer is a separate concern).
- Creating the actual git clone inside `clones/` (only the empty directory is created).
- Updating `deploy/.env` or any deployment-level env documentation for `RUNTIME_BASE_ROOT`.
- Changing Control API logic that decides what value to pass as `runtime_root` in the request body.

## Acceptance criteria

- With `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime`, importing `/Users/pierrebocquet/test-ai-dev` causes the supervisor to create `/Users/pierrebocquet/runtime/test-ai-dev/{clones,worktrees,runs,state,logs}` — no path under `/runtime/projects/` is attempted.
- Without `RUNTIME_BASE_ROOT` set but with `AI_DEV_FACTORY_RUNTIME_ROOT=/Users/pierrebocquet/runtime/ai-dev-factory`, `_runtime_base_root()` resolves to `/Users/pierrebocquet/runtime`.
- Supervisor returns `{"error": "runtime_base_root_not_writable", "detail": "/runtime"}` (HTTP 422) when the resolved base root is not writable, instead of an unhandled `OSError`.
- Supervisor bootstrap log line includes `runtime_base_root=`, `project_runtime_root=`, `project_id=`, `project_root=`.
- `pytest tests/test_project_id.py` passes with the updated assertions.
- `pytest tests/test_project_bootstrap.py` passes with the updated mock response and path assertions.
- The existing `ai-dev-factory` runtime at `/Users/pierrebocquet/runtime/ai-dev-factory` is not touched by any code path introduced in this ticket.
