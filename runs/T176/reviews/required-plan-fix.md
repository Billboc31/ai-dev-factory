# Required Plan Fix — T176

## Problem

The current plan introduces a `runtime_root` field in the UI/API but explicitly excludes backend wiring for that override.

This creates a mismatch:

- the UI suggests runtime root selection is supported;
- the backend still behaves as if runtime root is auto-resolved only.

This would produce confusing behavior and make debugging runtime ownership harder.

## Required fix

The plan must include full backend support for `runtime_root` override.

## Additional required scope

### Backend — runtime root resolution

Add a central runtime root resolution helper:

```text
_resolve_runtime_root(...)
```

that:

- uses explicit `runtime_root` override if provided;
- otherwise falls back to auto-detected runtime root;
- validates ownership and consistency.

### Validation

Validate that:

- sandbox_dir is inside runtime_root;
- source_path is inside sandbox_dir;
- runtime_root exists or can be created;
- runtime_root does not escape allowed roots.

Reject invalid runtime overrides with explicit diagnostics.

### Persistence

Persist the effective runtime root in `SandboxState`.

### Logging

Before deploy:

```text
runtime_root=<effective runtime root>
runtime_root_source=<auto|override>
```

### UI behavior

If advanced runtime options are hidden:

- runtime_root remains auto-configured.

If the user overrides runtime_root:

- show the effective sandbox destination preview live.

## Acceptance criteria additions

- runtime_root override actually changes deploy target
- invalid runtime_root values fail validation explicitly
- logs clearly indicate whether runtime root was auto or overridden
- sandbox paths are derived from the effective runtime root
- UI preview updates when runtime_root changes