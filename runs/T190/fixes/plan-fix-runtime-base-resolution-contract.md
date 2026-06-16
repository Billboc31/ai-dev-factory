# T190 plan fix — runtime base resolution contract

The T190 plan must make the runtime base resolution explicit and observable.

The current failure happened because the supervisor silently used a container-style absolute path:

```text
/runtime/projects/<project_id>
```

That must never happen silently again.

## Required runtime model

There are two distinct concepts:

```text
AI_DEV_FACTORY_RUNTIME_ROOT
```

Runtime root of the AI Dev Factory project itself.

Example:

```text
/Users/pierrebocquet/runtime/ai-dev-factory
```

and:

```text
RUNTIME_BASE_ROOT
```

Parent directory containing one runtime root per managed project.

Example:

```text
/Users/pierrebocquet/runtime
```

For an imported project `test-ai-dev`, the project runtime root is:

```text
/Users/pierrebocquet/runtime/test-ai-dev
```

not:

```text
/runtime/projects/test-ai-dev
```

and not:

```text
/Users/pierrebocquet/runtime/ai-dev-factory/projects/test-ai-dev
```

## Required resolution order

Supervisor resolves `runtime_base_root` in this order:

1. `RUNTIME_BASE_ROOT` if explicitly set.
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT` if set.
3. `Path.home() / "runtime"` as local fallback.

It must not default to `/runtime` unless explicitly configured.

## Required diagnostics

On every project bootstrap, supervisor must log:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

This log must appear before directory creation.

## Required error handling

If the resolved runtime base root is not writable, supervisor must return a structured HTTP error instead of crashing.

Example payload:

```json
{
  "error": "runtime_base_root_not_writable",
  "detail": "/runtime"
}
```

## Acceptance criteria

- No code path creates `/runtime/projects/...` unless `/runtime` was explicitly configured as `RUNTIME_BASE_ROOT` and is writable.
- Bootstrap with `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime` creates `/Users/pierrebocquet/runtime/<project_id>/...`.
- Bootstrap without `RUNTIME_BASE_ROOT` but with `AI_DEV_FACTORY_RUNTIME_ROOT=/Users/pierrebocquet/runtime/ai-dev-factory` resolves base root to `/Users/pierrebocquet/runtime`.
- Bootstrap logs the resolved paths before `mkdir`.
- Read-only filesystem errors are converted to structured supervisor errors.
