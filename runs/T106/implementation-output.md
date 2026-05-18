Both fixes are correct. Here's a summary:

**Files modified (2):**

| File | Change |
|------|--------|
| `services/control_api/routes/project_map.py` | `POST /project-map/refresh` now reads `worktrees_dir` from `request.app.state.worktrees_dir` and passes it as a keyword arg to the service |
| `services/control_api/services/project_map_service.py` | `refresh_project_map` gains a `worktrees_dir: Path | None = None` parameter and appends `--worktrees-dir` to the subprocess command when provided |

The blocking issue is fixed: the dashboard "Refresh map" button now launches the mapper with the correct worktrees directory, so worktree-mode ticket statuses will be read properly instead of all appearing as `not_ingested`.
