## Objective

Eliminate the remaining hidden coupling between per-environment deployments and
the host ai-dev-factory checkout by ensuring the per-sandbox supervisor, all
runtime script execution, and cleanup operations use the cloned project source
as their working root when a branch ref is specified.

## Included

### 1. `tools/agent_runner/run_sandbox.py` — `_start_sandbox_supervisor()`

Add an optional `source_root: Path | None = None` parameter.

Resolution logic:
- If `source_root` is provided and `source_root / "services" / "supervisor" / "main.py"` exists,
  start the supervisor with `cwd=str(source_root)` so the cloned branch's
  supervisor implementation runs.
- Otherwise fall back to `cwd=str(repo_root)` (host ai-dev-factory, unchanged
  behaviour for projects that do not ship a supervisor).

The `cmd` list (`python -m uvicorn services.supervisor.main:app ...`) stays
identical; only `cwd` changes.

### 2. `services/control_api/services/sandbox_runtime_deploy.py` — `deploy_operational_runtime()`

Pass `source_path` to `rs._start_sandbox_supervisor()` when `state.ref` is set:

```python
supervisor_proc = rs._start_sandbox_supervisor(
    state.supervisor_port,
    runtime_root,
    log_path,
    source_root=source_path if state.ref else None,
)
```

### 3. `services/control_api/services/sandbox_runtime_deploy.py` — `_docker_logs_section()`

Replace `cwd=state.project_root` with the source path when `state.source_path`
is populated:

```python
cwd = state.source_path or state.project_root
```

### 4. `services/supervisor/main.py` — `_do_sandbox_stop()` and `sandbox_delete()`

Both functions currently read only `state.get("worktree_path")`.  After T171 the
state file written by `run_sandbox.py` may carry `source_path` instead.

- `_do_sandbox_stop()`: resolve the runtime path as
  `state.get("source_path") or state.get("worktree_path")`, rename the local
  variable accordingly, update `_run_stop_sh_supervisor` call-sites.
- `sandbox_delete()`: same resolution; when the path came from `source_path`
  (plain clone), use `shutil.rmtree` directly instead of first attempting
  `git worktree remove --force`.

### 5. Tests

New or extended test file (`tests/test_sandbox_supervisor_isolation.py` or
added to the existing sandbox test suite):

- `test__start_sandbox_supervisor_uses_source_root_when_present`: mock a
  `source_root` directory containing `services/supervisor/main.py`; assert
  `subprocess.Popen` is called with `cwd=str(source_root)`.
- `test__start_sandbox_supervisor_falls_back_to_host_root`: no
  `services/supervisor/main.py` in `source_root`; assert `cwd` is the host
  `repo_root`.
- `test_docker_logs_section_uses_source_path`: `state.source_path` set;
  assert `subprocess.run` receives `cwd=state.source_path`.
- `test_do_sandbox_stop_reads_source_path`: state dict contains `source_path`
  but no `worktree_path`; assert `_run_stop_sh_supervisor` is called with the
  correct path.

### 6. Architecture boundary document

Create `docs/architecture/runtime-boundary.md` documenting:
- Control plane responsibilities (orchestration, registry, lifecycle, infra)
- Project runtime responsibilities (all scripts, supervisor, daemon, compose)
- The rule: "when `state.ref` is set, every execution context resolves from
  `sandbox_dir/source/`, never from the host checkout"

## Excluded

- Changing how the global control-plane supervisor (`deploy/start_supervisor.sh`,
  `services/supervisor/main.py` daemon endpoints) resolves its own paths — it
  is not an environment runtime component.
- Adding project-level supervisor interface versioning or negotiation.
- Replacing the existing `_clone_fresh_source()` logic introduced by T171.
- Changing the `.ai-dev-factory/scripts/` convention or how scripts are
  discovered.
- Daemon/worker isolation beyond the per-sandbox supervisor already started
  by `deploy_operational_runtime()`.
- UI or API surface changes.

## Acceptance criteria

- `_start_sandbox_supervisor()` accepts `source_root`; when
  `source_root/services/supervisor/main.py` is present, `subprocess.Popen` is
  called with `cwd=str(source_root)`.
- `_start_sandbox_supervisor()` falls back to `cwd=repo_root` for projects that
  do not define a supervisor (no regression for non-ai-dev-factory projects).
- `deploy_operational_runtime()` passes `source_path` to
  `_start_sandbox_supervisor()` when `state.ref` is set.
- `_docker_logs_section()` uses `state.source_path` as cwd when it is
  non-empty.
- `_do_sandbox_stop()` and `sandbox_delete()` in `supervisor/main.py` accept a
  state dict carrying `source_path` without `worktree_path` and correctly run
  the stop script / remove the directory.
- All four new unit tests pass.
- `docs/architecture/runtime-boundary.md` exists and states the boundary rule.
- Deploying the same project from two different branches simultaneously (e.g.
  T170 and main) starts two independent per-sandbox supervisors, each rooted
  in their own `sandbox_dir/source/`.
