Implementation complete. Here's the summary:

## Files created/modified

**New files:**
- `services/supervisor/path_mapper.py` — `ContainerToHostMapper` class reading `CONTAINER_RUNTIME_ROOT` / `HOST_RUNTIME_ROOT` env vars
- `tests/test_host_path_mapping.py` — 4 unit tests for the mapper
- `tests/test_analysis_worktree_isolation.py` — 5 tests verifying worktree creation, file isolation, cleanup on success/failure, and state JSON

**Modified files:**
- `services/supervisor/main.py` — imports and instantiates mapper at module load; applies `mapper.map()` to `project_root` in `POST /analysis/start`; logs original→mapped path; forwards `--worktrees-dir` to subprocess; adds `GET /supervisor/status`
- `tools/agent_runner/run_analysis.py` — adds `--worktrees-dir` arg; on startup creates isolated worktree via `create_ticket_branch_and_worktree`; redirects all file writes and `commit_and_push` to `write_root` (worktree when provided, else `project_root` for backwards compat); cleans up worktree in `finally`; includes `worktree_path` in all state writes
- `services/control_api/models/schemas.py` — added `worktree_path: str | None = None` to `AnalysisStatus`
- `apps/dashboard/src/pages/DeployerPage.jsx` — `AnalysisStatusPanel` displays `Worktree: {path}` when non-null

The backwards-compatibility design: when `--worktrees-dir` is absent (existing tests), `write_root = project_root` and no worktree is created — all 9 pre-existing `test_run_analysis.py` tests pass unchanged.
