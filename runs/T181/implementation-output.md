All tasks complete. Here's a summary of what was implemented:

## Summary

### Files created
- `services/control_api/services/project_id.py` — `normalize_project_id`, `validate_project_id`, `assert_contained` (path traversal prevention)
- `services/control_api/services/stack_detector.py` — `detect_stack` heuristics (python/node/go/rust/unknown)
- `services/control_api/services/project_bootstrap.py` — `bootstrap()` orchestrating validation → directory creation → project.yml write → registry registration
- `apps/dashboard/src/pages/ProjectsPage.jsx` — project listing with "Import project" button
- `apps/dashboard/src/pages/ImportProjectPage.jsx` — two-field form with auto-normalize preview
- `tests/test_project_id.py` — 24 tests for normalize/validate/assert_contained
- `tests/test_project_bootstrap.py` — 11 tests including containment assertion
- `tests/test_project_registry_persistence.py` — 10 tests for register/unregister/load_from_workspace_file

### Files modified
- `services/control_api/services/project_registry.py` — added `register`, `unregister`, `load_from_workspace_file` with `workspace.json` persistence
- `services/control_api/services/runtime_resolver.py` — added `resolve_project_runtime_root` + optional `project_id` param on all 4 directory resolvers
- `services/control_api/models/schemas.py` — added `ProjectImportRequest`, `BootstrapResult`, extended `ProjectInfo` with `runtime_root`/`stack`
- `services/control_api/routes/projects.py` — added `GET /projects`, `POST /projects/import`, `DELETE /projects/{id}`
- `services/control_api/main.py` — exposes `runtime_root` on `app.state`, prefers workspace file in runtime-configured (Docker/systemd) mode
- `services/supervisor/main.py` — added per-project daemon `start/status/stop` endpoints with full runtime path logging and registry validation
- `apps/dashboard/src/api/projects.js` — added `listProjects`, `importProject`, `deleteProject`
- `apps/dashboard/src/App.jsx` — added `/projects` and `/import-project` routes + "Projects" nav link

**Test results**: 74 new/related tests pass, 0 regressions introduced (66 pre-existing failures unchanged).
