Here is the implementation plan:

---

## Objective

Eliminate the remaining hidden coupling between per-environment deployments and the host ai-dev-factory checkout by ensuring the per-sandbox supervisor, all runtime script execution, and cleanup operations use the cloned project source as their working root when a branch ref is specified.

## Included

### 1. `tools/agent_runner/run_sandbox.py` — `_start_sandbox_supervisor()` (line 979)

Add `source_root: Path | None = None` parameter. When `source_root/services/supervisor/main.py` exists, spawn the supervisor with `cwd=str(source_root)` so the cloned branch's supervisor implementation runs. Otherwise fall back to `cwd=str(repo_root)` (host, unchanged behaviour for non-ai-dev-factory projects).

### 2. `services/control_api/services/sandbox_runtime_deploy.py` — `deploy_operational_runtime()` (line 325)

Pass `source_path` to `rs._start_sandbox_supervisor()` when `state.ref` is set.

### 3. `services/control_api/services/sandbox_runtime_deploy.py` — `_docker_logs_section()` (line 186)

Replace `cwd=state.project_root` with `state.source_path or state.project_root`.

### 4. `services/supervisor/main.py` — `_do_sandbox_stop()` and `sandbox_delete()` (lines 1130, 1182)

Both functions read only `state.get("worktree_path")`. Extend to also check `state.get("source_path")`, preferring it when present. For plain clone paths (`source_path`), use `shutil.rmtree` directly instead of `git worktree remove`.

### 5. Tests

Four new unit tests covering: supervisor uses source_root cwd, fallback to host root, `_docker_logs_section` uses source_path, supervisor stop handles source_path-only state.

### 6. `docs/architecture/runtime-boundary.md`

New file documenting the control-plane vs. project-runtime split and the rule that all execution contexts resolve from `sandbox_dir/source/` when `state.ref` is set.

## Excluded

- Changing the global control-plane supervisor's own path resolution
- Project-level supervisor interface versioning or negotiation
- Replacing T171's `_clone_fresh_source()` logic
- Changing the `.ai-dev-factory/scripts/` discovery convention
- Daemon/worker isolation beyond the per-sandbox supervisor
- UI or API surface changes

## Acceptance criteria

- `_start_sandbox_supervisor()` uses `cwd=str(source_root)` when `source_root/services/supervisor/main.py` exists; falls back to host root otherwise
- `deploy_operational_runtime()` passes `source_path` to `_start_sandbox_supervisor()` when `state.ref` is set
- `_docker_logs_section()` uses `state.source_path` as cwd when non-empty
- `_do_sandbox_stop()` and `sandbox_delete()` handle `source_path`-only state correctly
- All four new unit tests pass
- `docs/architecture/runtime-boundary.md` exists and states the boundary rule
- Two environments deploying different branches simultaneously each have independent per-sandbox supervisors rooted in their own `sandbox_dir/source/`
