T193 is complete. All 7 plan changes were implemented and merged via PR #238:

1. **`runtime_resolver.py`** — fixed `resolve_state_dir` fallback returning `state/` not `runs/`
2. **`artifact_reader.py`** — threaded `project_runtime_root` through all public functions
3. **`board_service.py`** — added `project_runtime_root` param; skips SQLite for non-factory projects
4. **`daemon_manager.py`** — routes lifecycle calls to `/projects/{id}/daemon/*` endpoints when `project_id` is set
5. **`routes/daemon.py`** — injects `project_id` + `project_runtime_root` into all project-scoped handlers
6. **`routes/tickets.py`** — forwards `project_runtime_root` to all `artifact_reader` calls
7. **`supervisor/main.py`** — injects `AI_DEV_FACTORY_RUNTIME_ROOT` into per-project daemon subprocess env

8 new tests all pass. The 21 pre-existing failures in `test_control_api_artifacts.py` / `test_ticket_timeline.py` are unrelated to T193 (confirmed by running them on the original codebase).
