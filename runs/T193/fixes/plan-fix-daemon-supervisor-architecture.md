# Plan fix — clarify and include project daemon architecture

The current T193 plan correctly scopes board/runs/log reads to the selected project's `project_runtime_root`, but the daemon lifecycle part is not safe enough.

## Required fix

The plan must explicitly choose and implement a project daemon architecture.

Preferred architecture: supervisor-backed project daemons.

Control API should not silently spawn project daemons locally from inside the API container unless that is explicitly intended and proven safe. Starting/stopping daemon processes is a host process lifecycle operation and previous project import/bootstrap work established that host filesystem operations must go through the supervisor.

## Required changes to the plan

### Control API responsibilities

For project daemon start/stop/restart/status/logs, Control API must:

1. Resolve selected `project_id` from the route.
2. Resolve `project_root` from the registry.
3. Resolve persisted `project_runtime_root` from the registry.
4. Call the supervisor project-daemon endpoint with:

```json
{
  "project_id": "<project_id>",
  "project_root": "<project_root>",
  "project_runtime_root": "<project_runtime_root>",
  "exec_cmd": "<exec_cmd>",
  "restart_policy": "<restart_policy>"
}
```

5. Return the supervisor response to the UI.

### Supervisor responsibilities

Supervisor must:

1. Keep one daemon state/process per project.
2. Start daemon with:

```text
AI_DEV_FACTORY_RUNTIME_ROOT=<project_runtime_root>
```

3. Use the correct project cwd, usually `project_root` or the managed clone path if the project has been cloned into its runtime.
4. Write PID/status/log files under the selected project's runtime root.
5. Never mutate the ai-dev-factory daemon when a different project daemon is started/stopped.

### Board/runs/logs responsibilities

Board, run, ticket and log reads must continue to use the persisted `project_runtime_root` and must not fall back to the global ai-dev-factory runtime when a project is selected.

## Acceptance additions

- Starting daemon for `test-ai-dev` creates/updates only `test-ai-dev` daemon state.
- Stopping daemon for `test-ai-dev` does not stop `ai-dev-factory` daemon.
- Project daemon logs/PID/status live under `test-ai-dev`'s persisted runtime root.
- The daemon process env includes `AI_DEV_FACTORY_RUNTIME_ROOT=<test-ai-dev project_runtime_root>`.
- The implementation includes tests for the chosen daemon architecture.
- No implementation path starts project daemons from Control API inside Docker unless a test proves the path/mount model is valid.

## Review verdict

PLAN_FIX_REQUIRED until this architecture is included in `runs/T193/plan.md`.
