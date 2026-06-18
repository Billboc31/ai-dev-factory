The plan is written at `runs/T193/plan.md`. Here is what it covers:

---

## Objective
Thread `project_runtime_root` through all read paths and route project-daemon lifecycle calls to the supervisor's per-project endpoints.

## Seven concrete changes

| # | File | Change |
|---|------|--------|
| 1 | `runtime_resolver.py` | Fix `resolve_state_dir` fallback: `/ "runs"` → `/ "state"` |
| 2 | `artifact_reader.py` | Add `project_runtime_root` param to `_runs_root` and all public functions |
| 3 | `board_service.py` | Thread `project_runtime_root` through `get_board`; skip global SQLite DB when project is selected |
| 4 | `daemon_manager.py` | Add `project_id` + `project_runtime_root` params; route to `/projects/{id}/daemon/*` when `project_id` is set |
| 5 | `routes/daemon.py` | Inject `project_id` and `project_runtime_root` into all project-scoped daemon calls |
| 6 | `routes/tickets.py` | Forward `project_runtime_root` from DI into `artifact_reader` call sites |
| 7 | `supervisor/main.py` | Inject `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}` into the Popen env for `project_daemon_start` |

## Eight test cases
Covering: state_dir fix, artifact reader isolation, board isolation, SQLite skip, supervisor routing for start/stop/status, backward compatibility for global routes, and Popen env injection.

## Key architecture decision (explicit)
Supervisor-backed project daemons. The Control API never starts project daemons locally — all lifecycle calls go to supervisor `/projects/{project_id}/daemon/*`. The supervisor already has these endpoints; it just needs to inject the env var on spawn.
