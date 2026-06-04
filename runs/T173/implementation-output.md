All 49 tests pass. Here's a summary of the changes made:

---

## Changes made

### `services/control_api/services/sandbox_runtime_deploy.py`

**`_clone_fresh_source`** (line 194):
- Signature changed from `ref: str` → `ref: str | None`
- Clone command omits `--branch` when `ref is None` (clones default branch)
- Branch-mismatch check guarded by `if ref is not None`

**`deploy_operational_runtime`** (line 279):
- Removed `sandbox_dir / "source" if state.ref else project_root` — now always `source_path = sandbox_dir / "source"`

**Lines 386–424**:
- Removed `if state.ref:` guard — clone is now unconditional (`state.ref` may be `None`)
- Added path validation guard: resolves `source_path` and calls `.relative_to(sandbox_dir)`; if it escapes, returns `OperationalDeployResult(success=False)` immediately with a clear error
- Added `resolved script path: …` log line for each required script before execution

### `tests/test_sandbox_runtime_deploy.py`

- Added `import shutil`
- `_sample_state`: pre-creates `sandbox_dir/source/.ai-dev-factory/scripts/` to reflect the clone-based layout
- `test_deploy_operational_runtime_success`, `test_deploy_operational_runtime_script_failure_cleans_up`, `test_deploy_runs_smoke_for_deploy_and_test_mode`: added `_clone_fresh_source` patch
- **New** `test_deploy_operational_runtime_clones_even_without_ref`: asserts clone is called with `ref=None` and `_run_scripts` receives `sandbox_dir/source`
- **New** `test_deploy_operational_runtime_path_validation_fails`: uses a symlink pointing outside `sandbox_dir` to trigger the guard

### `tests/test_environment_infra_bootstrap.py` / `tests/test_environment_supervisor.py`

- Added `_clone_fresh_source` patch to the three tests that call `deploy_operational_runtime` without setting `state.ref`
