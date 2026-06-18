The plan is written at `runs/T193/plan.md`. Here is what it covers:

**Architecture decision (explicit):** Supervisor-backed project daemons. The Control API never spawns daemon processes locally — all project daemon lifecycle calls go through the supervisor's `/projects/{project_id}/daemon/*` endpoints with `project_id`, `project_root`, `project_runtime_root`, `exec_cmd`, and `restart_policy` in the body.

**Seven files in scope:**

1. `runtime_resolver.py` — add `project_runtime_root` param to all resolve functions; fix `resolve_state_dir` bug
2. `daemon_manager.py` — thread `project_id` + `project_runtime_root` through all functions; route to supervisor project endpoint when `project_id` is set
3. `routes/daemon.py` — forward both params from dependency injection into daemon_manager calls
4. `artifact_reader.py` — add `project_runtime_root` to `_runs_root()` and all public functions
5. `board_service.py` — pass `project_runtime_root` into resolver calls; no global fallback
6. `routes/tickets.py` — forward `project_runtime_root` from DI into artifact_reader and board_service
7. `supervisor/main.py` — verify/fix `AI_DEV_FACTORY_RUNTIME_ROOT` env injection and per-project PID/log isolation

**Seven concrete test cases** covering board isolation, artifact reader isolation, daemon manager supervisor routing, global endpoint preservation, supervisor env injection, PID file isolation, and route propagation.
