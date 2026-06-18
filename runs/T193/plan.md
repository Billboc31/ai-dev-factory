The plan is written. Here's a summary of what it covers:

**Architecture decision:** supervisor-backed project daemons (Option A from the review). The plan explicitly forbids the control API from calling global supervisor endpoints for project-scoped routes.

**Root causes identified and fixed:**

1. **`daemon_manager.py`** — calls `/daemon/start`, `/daemon/stop`, `/daemon/status` (global) for all projects. Fixed to call `/projects/{project_id}/daemon/*` when `project_id` is provided.

2. **`supervisor/main.py`** — `project_daemon_start` does not set `AI_DEV_FACTORY_RUNTIME_ROOT` in the spawned daemon env. Fixed to inject it from `body.project_runtime_root` (passed by control API) or computed from env.

3. **`routes/daemon.py`** — project-scoped handlers don't forward `project_id` or `project_runtime_root` to `daemon_manager`. Fixed.

4. **`board_service.py`** — ignores `project_runtime_root`, reads global DB. Fixed with no-fallback rule.

5. **`artifact_reader.py`** — `list_tickets`/`get_ticket_logs` use global runs dir. Fixed with explicit `runs_dir` param.

6. **`routes/tickets.py`** — project-scoped endpoints don't propagate `project_runtime_root` to artifact reader. Fixed.

**7 concrete test cases** covering board isolation, daemon manager supervisor call routing, and supervisor subprocess env injection.
