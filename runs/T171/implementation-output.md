All tests pass. Here's a summary of what was implemented:

## Changes

**`services/control_api/models/sandbox.py`**
- Added `source_path: str | None = None` field to `SandboxState` alongside `worktree_path` (kept for backward compat of serialized state)

**`services/control_api/services/sandbox_runtime_deploy.py`**
- Added `_clone_fresh_source(project_root, source_path, ref, log)` — does `git clone --branch <ref>`, logs `pwd` / `git branch --show-current` / `git rev-parse --short HEAD`, and aborts if checked-out branch ≠ requested ref
- `deploy_operational_runtime`: removed `use_worktree` (was dead code), always uses `sandbox_dir/source` when `state.ref` is set, calls `_clone_fresh_source` before any script runs; aborts deployment on clone/verification failure

**`services/control_api/services/sandbox_manager.py`**
- Renamed `create_with_worktree` → `create_with_source`: replaces `git fetch` + `git worktree add` with `git clone --branch <branch>`, verifies branch post-clone, stores `source_path` on state
- `destroy`: prefers `source_path` (removed via `shutil.rmtree`); falls back to legacy `worktree_path` + `git worktree remove` for old state files

**`services/control_api/services/deployer_runner.py`**
- `_do_deploy`: resolves `cwd` from `sandbox.source_path` first, then legacy `worktree_path`, then `project_root`
- `run_deploy_sandboxed`: calls `create_with_source` instead of `create_with_worktree`

**`services/control_api/routes/sandbox.py`**
- `cleanup_sandbox_run`: removes `source/` first via `shutil.rmtree`; keeps legacy `worktree/` cleanup for backward compat

**`tests/test_sandbox_manager.py`** — 3 new tests + updated worktree test:
- `test_source_removed_after_undeploy`, `test_legacy_worktree_removed_after_undeploy`
- `test_create_with_source_uses_clone`, `test_create_with_source_aborts_on_clone_failure`, `test_create_with_source_aborts_on_branch_mismatch`

**`tests/test_sandbox_runtime_deploy.py`** — 2 new tests:
- `test_deploy_operational_runtime_clones_fresh_source_on_ref`, `test_deploy_operational_runtime_aborts_on_clone_failure`
