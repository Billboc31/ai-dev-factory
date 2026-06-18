# Plan review — daemon lifecycle fix required

The current T193 plan correctly identifies the board/data isolation problem: project boards must read from the selected project's persisted `project_runtime_root`, not from the global ai-dev-factory runtime database.

However, the plan is incomplete for daemon lifecycle.

## Blocking concern

The plan proposes changing `services/control_api/services/daemon_manager.py` so the Control API starts project daemons locally with `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}`.

This is risky and likely wrong when the Control API runs in Docker:

- Control API container paths are not host paths.
- Project roots and runtime roots may require host filesystem access.
- Previous import/bootstrap fixes established that host filesystem operations must go through the supervisor.
- Starting a daemon is a host process lifecycle operation and should not silently happen inside the API container unless that is explicitly intended and tested.

## Required clarification

The plan must explicitly define one of these architectures:

### Option A — Supervisor-backed project daemons preferred

Project daemon start/stop/restart/status/logs go through the supervisor.

Control API responsibilities:

- resolve selected project via registry
- resolve persisted `project_runtime_root`
- call supervisor project-daemon endpoint with `project_id`, `project_root`, `project_runtime_root`, `exec_cmd`, and `restart_policy`
- expose the supervisor response to the UI

Supervisor responsibilities:

- start one daemon per project
- set `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}` for the daemon process
- use `cwd={project_root}` or the correct project clone/worktree path
- write PID/status/logs under that project's runtime root
- never share daemon state between projects

### Option B — Container-local project daemons

If the intended design is to run project daemons inside the Control API container, the plan must justify it and prove all required paths are mounted and mapped correctly.

It must include tests proving that a project daemon for an imported host project can read/write the selected project runtime without leaking to ai-dev-factory.

## Required plan changes

- Do not leave project daemon lifecycle half-scoped.
- Board/runs/logs isolation and daemon process isolation must use the same `project_runtime_root` source of truth.
- The plan must state whether `project_daemon_start`, `project_daemon_stop`, `project_daemon_restart`, `project_daemon_status`, and project daemon logs are supervisor-backed or container-local.
- If supervisor-backed, include supervisor endpoint changes in scope.
- If container-local, include explicit Docker path/mount validation and tests.

## Acceptance additions

- Starting a daemon for `test-ai-dev` does not start or mutate the ai-dev-factory daemon.
- Stopping a daemon for `test-ai-dev` does not stop the ai-dev-factory daemon.
- Daemon PID/status/log path is under `test-ai-dev`'s persisted runtime root.
- The daemon process environment contains `AI_DEV_FACTORY_RUNTIME_ROOT={test-ai-dev project_runtime_root}`.
- The implementation has a test for the selected daemon architecture.

## Review verdict

PLAN_FIX_REQUIRED until daemon lifecycle architecture is clarified and included.