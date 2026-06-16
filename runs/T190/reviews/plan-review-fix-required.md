# Plan review — fix required

The current T190 plan fixes the immediate `/runtime/projects/...` failure, but it is incomplete as a durable architecture fix.

## Required fixes before implementation

### 1. Persist `project_runtime_root` as the source of truth

The supervisor may compute the initial project runtime root during bootstrap, but after that the value must be persisted and reused.

After bootstrap, routes must not recompute the project runtime root from:

- `project_id`
- `RUNTIME_BASE_ROOT`
- `AI_DEV_FACTORY_RUNTIME_ROOT`
- `runtime_root`
- `/projects/<project_id>` conventions

Required flow:

1. Supervisor resolves `runtime_base_root`.
2. Supervisor computes `project_runtime_root = runtime_base_root / project_id`.
3. Supervisor creates `project_runtime_root/{clones,worktrees,runs,state,logs}`.
4. Supervisor returns `project_runtime_root` in the bootstrap response.
5. Control API persists `project_runtime_root` in the project registry.
6. All daemon/worktree/log/ticket operations use the persisted `project_runtime_root`.

Acceptance additions:

- `project_runtime_root` is persisted per project.
- API restart does not change the project runtime root.
- Runtime path helpers use persisted `project_runtime_root` when available.

### 2. Make runtime base resolution explicit and observable

The supervisor must not silently fall back to `/runtime`.

Resolution order:

1. `RUNTIME_BASE_ROOT`
2. parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `Path.home() / "runtime"`

Supervisor bootstrap must log before directory creation:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

If the resolved runtime base root is not writable, return a structured HTTP error instead of crashing.

Example:

```json
{
  "error": "runtime_base_root_not_writable",
  "detail": "/runtime"
}
```

## Review verdict

PLAN_FIX_REQUIRED

The plan can be approved once it explicitly persists `project_runtime_root` and treats it as the durable runtime location for every project operation.
