Now I have the full picture. Writing the V1 plan.

## Objective

Introduce Docker-to-host path mapping in the supervisor and isolated git worktrees for analysis jobs, so that analysis never runs directly in the main project root and the supervisor never passes Docker-internal container paths to subprocesses.

## Included

### 1. Path mapper utility — `services/supervisor/path_mapper.py` *(new)*

- `ContainerToHostMapper` class with a single method `map(path: str) -> str`.
- Reads `CONTAINER_RUNTIME_ROOT` and `HOST_RUNTIME_ROOT` from env at construction time.
- Returns the host-equivalent path by replacing the container prefix; returns the path unchanged when env vars are absent.
- Logs both the original and mapped path at INFO level on every translation.

### 2. Apply path mapping in `services/supervisor/main.py`

- Instantiate `ContainerToHostMapper` at module load time.
- In `POST /analysis/start`: apply `mapper.map(project_root)` to the received `project_root` before it is passed to the `run_analysis.py` subprocess.
- Expose `container_runtime_root` and `host_runtime_root` fields in `GET /supervisor/status` so the mapping config is inspectable.

### 3. Isolated analysis worktree in `tools/agent_runner/run_analysis.py`

- At startup, derive `job_id` from `project_id + timestamp` (e.g. `analysis-{project_id}-{YYYYMMDDTHHMMSS}`).
- Call `worktree_manager.create_ticket_branch_and_worktree(job_id, branch=f"analysis/{job_id}", worktrees_dir, repo_root)` — reuses the existing utility unchanged.
- Redirect all file writes, `git add`, `git commit`, and `git push` operations to the isolated worktree path instead of `project_root`.
- Accept `--worktrees-dir` as a new CLI argument (default: `{RUNTIME_ROOT}/worktrees`).
- Wrap the entire job body in `try/finally`; call `worktree_manager.remove_ticket_worktree(job_id, worktrees_dir, force=True)` in the `finally` block on both success and failure paths.
- Add `worktree_path` to the state JSON written by `_write_state()`.

### 4. Pass `--worktrees-dir` from `services/supervisor/main.py`

- In `POST /analysis/start`, extend the subprocess command list to include `--worktrees-dir {_worktrees_dir()}`. The helper already exists; just forward it to the subprocess.

### 5. Expose `worktree_path` in analysis status

- **`services/control_api/`** — the `AnalysisStatus` model already proxies the JSON written by `run_analysis.py`; adding `worktree_path: str | None = None` to the model is sufficient.
- **`apps/dashboard/src/pages/DeployerPage.jsx`** — in `AnalysisStatusPanel`, add a single line beneath the branch/PR fields that shows `Worktree: {status.worktree_path}` (greyed out / omitted when null).
- **`apps/dashboard/src/api/deployer.js`** — no change needed; the field flows through automatically.

### 6. Tests

- **`tests/test_host_path_mapping.py`** *(new)* — unit-tests `ContainerToHostMapper`:
  - correct translation when both env vars set,
  - identity when env vars absent,
  - path-inside-subdir preserved,
  - unrelated paths not mutated.
- **`tests/test_analysis_worktree_isolation.py`** *(new)* — tests `run_analysis.py` main():
  - `worktree_manager.create_ticket_branch_and_worktree` is called (monkeypatched),
  - file writes go to the worktree path, not to the original `project_root`,
  - `remove_ticket_worktree` is called in both success and simulated-failure paths,
  - `worktree_path` is present in the written state JSON.

## Excluded

- `run_scripts.py` isolation (not in V1).
- Deploy sandbox isolation (compose project names, dynamic ports, env files).
- Job-scoped runtime directory layout redesign.
- Cleanup API endpoints (`POST /deployer/analysis/cleanup`).
- Dashboard isolation-status badge beyond showing the raw worktree path.
- Tester agent, deploy/test/fix retry loop, production or remote deployment.
- Migration of existing historical state files.

## Acceptance criteria

- `ContainerToHostMapper("/app/runs/T100")` returns `"/Users/pierre/runtime/ai-dev-factory/runs/T100"` when `CONTAINER_RUNTIME_ROOT=/app` and `HOST_RUNTIME_ROOT=/Users/pierre/runtime/ai-dev-factory`; returns the input path unchanged when neither var is set.
- Supervisor logs show the original container path and the resolved host path on each analysis start.
- `run_analysis.py` never writes files directly under the original `project_root`; all writes and git operations target the isolated worktree directory.
- After a simulated analysis job exits (success path and exception path), `RUNTIME_ROOT/worktrees/analysis-*/` no longer exists on disk.
- `GET /projects/{project_id}/deployer/analysis/status` includes a non-null `worktree_path` field while a job is running.
- The dashboard analysis status panel displays the worktree path when available.
- `pytest tests/` passes without modification to any existing test.
