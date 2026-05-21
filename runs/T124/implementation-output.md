All 19 new tests pass and no regressions introduced.

---

## Summary

**Files created (5):**
- `services/control_api/services/project_registry.py` — `ProjectRegistry` class that scans a `projects_root` for git subdirs or wraps a single root; exposes `list_projects(artifact_reader)` and `resolve(id)`
- `apps/dashboard/src/hooks/useProjects.js` — polls `GET /api/projects` every 10s via `usePolling`
- `apps/dashboard/src/components/ProjectSidebar.jsx` — renders project list with active highlight and click handler
- `tests/test_project_registry.py` — 10 unit tests (from_single_root, multi-root scan, non-git exclusion, worktree .git-file exclusion, tickets_count, resolve)
- `tests/test_projects_endpoint.py` — 9 integration tests (single/multi-root modes, tickets_count per project, regression checks for `/health` and `/daemon/status`)

**Files modified (3):**
- `services/control_api/main.py` — adds `projects_root` param to `create_app()`, reads `AI_DEV_FACTORY_PROJECTS_ROOT` env var, wires `ProjectRegistry` into `app.state`, adds `--projects-root` CLI arg
- `services/control_api/routes/providers.py` — `list_projects` now delegates to `request.app.state.project_registry.list_projects(artifact_reader)` (3-line body replacing 8)
- `apps/dashboard/src/App.jsx` — imports `useProjects` and `ProjectSidebar`; `Nav` receives `activeProject` prop instead of hardcoded string; layout gains a flex row with sidebar + main
