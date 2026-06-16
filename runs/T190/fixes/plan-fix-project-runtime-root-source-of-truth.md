# T190 plan fix — persist project_runtime_root as source of truth

The current T190 plan fixes the immediate `/runtime/projects/...` failure, but it still risks recomputing runtime paths in several places.

That is fragile.

## Required change

`project_runtime_root` must be persisted at import/bootstrap time and treated as the single source of truth for all later project operations.

After bootstrap, the system must not derive the project runtime root again from:

- `RUNTIME_BASE_ROOT`
- `AI_DEV_FACTORY_RUNTIME_ROOT`
- `runtime_root`
- `project_id`
- any `/projects/<project_id>` convention

The computed value must be stored in the project registry and reused everywhere.

## Expected flow

1. Supervisor resolves the runtime base root.
2. Supervisor computes:

```text
project_runtime_root = runtime_base_root / project_id
```

3. Supervisor creates:

```text
project_runtime_root/{clones,worktrees,runs,state,logs}
```

4. Supervisor returns `project_runtime_root` in the bootstrap response.
5. Control API persists `project_runtime_root` in the project registry.
6. Later daemon/worktree/log/ticket routes load the persisted `project_runtime_root` from the registry.

## Acceptance criteria

- `project_runtime_root` is persisted per project.
- The registry response for a project exposes the persisted `project_runtime_root`.
- Runtime paths for runs/worktrees/state/logs are derived from the persisted `project_runtime_root`.
- No route recomputes imported project runtime location from `project_id` after bootstrap.
- Restarting the API does not change the runtime root of an imported project.
