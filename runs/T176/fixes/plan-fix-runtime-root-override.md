# Plan Fix — Runtime Root Override Must Be Fully Wired

## Problem

The current T176 plan introduces a `runtime_root` field in the UI/API but explicitly excludes backend wiring for the override.

This creates a misleading UX where users can appear to choose a runtime root while the backend silently ignores it.

## Required fix

The plan must fully wire `runtime_root` override support end-to-end.

## Required backend additions

### Runtime root resolution

Add a central runtime root resolver:

```text
_resolve_runtime_root(...)
```

Behavior:

- use explicit override when provided;
- otherwise use auto-detected runtime root;
- validate ownership and consistency.

### Validation

Validate that:

- sandbox_dir belongs to runtime_root;
- source_path belongs to sandbox_dir;
- runtime_root exists or can be created safely;
- runtime_root cannot escape allowed sandbox/runtime roots.

### Persistence

Persist the effective runtime root in `SandboxState`.

### Logging

Before deploy:

```text
runtime_root=<effective runtime root>
runtime_root_source=<auto|override>
```

### UI behavior

When advanced runtime options are enabled:

- runtime_root override updates sandbox destination preview live.

## Acceptance criteria additions

- runtime_root override actually changes deploy target
- invalid runtime_root values fail validation explicitly
- logs clearly indicate runtime root source
- sandbox paths derive from effective runtime root
- UI preview updates when runtime_root changes