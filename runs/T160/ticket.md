# T160 — T160 - Fix environment sandbox path resolution and runtime root handling

**Source**: GitHub Issue #169

## Description

# T160 - Fix environment sandbox path resolution and runtime root handling

## Problem

The new Environments UI works visually, but runtime actions fail after creating a custom environment.

Example runtime error:

```text
[Errno 2] No such file or directory: '/sandboxes/demo-ai-dev-factory'
```

This indicates that environment actions rebuild sandbox paths incorrectly using:

```text
/sandboxes/<sandbox-id>
```

instead of resolving paths through the configured runtime root.

---

## Root cause hypothesis

Environment metadata or runtime services are likely:

- persisting a filesystem path instead of a sandbox id
- reconstructing sandbox paths using hardcoded `/sandboxes/...`
- bypassing the runtime resolver

The environment exists logically, but runtime actions resolve the sandbox from the wrong root.

---

# Goal

Make all environment runtime actions resolve sandbox paths exclusively through the global runtime resolver.

The runtime root must never be assumed to be `/`.

---

# Included

## Runtime path resolution audit

Audit all environment/sandbox runtime actions:

- Redeploy
- Stop
- Refresh
- Delete
- View Logs
- Status polling
- Environment detail loading

Verify all runtime path construction.

---

## Remove hardcoded `/sandboxes`

Remove any:

```text
/sandboxes/<id>
```

construction.

Disallow:

- `Path("/sandboxes")`
- string concatenation using `"/sandboxes/"`
- assuming runtime root is `/`

---

## Runtime resolver integration

All sandbox paths must be resolved through:

```text
runtime_resolver
```

or the canonical runtime root resolver already used by the platform.

Expected final behavior:

```text
<runtime_root>/sandboxes/<sandbox_id>
```

where:

```text
runtime_root
```

is configurable and environment-independent.

---

## Metadata model correction

Environment metadata must store:

```text
sandbox_id
```

NOT:

```text
/sandboxes/<id>
```

Filesystem paths must be reconstructed dynamically through the runtime resolver.

---

## Better runtime errors

If a sandbox is missing:

Return explicit errors such as:

```text
sandbox not found
```

Do not expose raw:

```text
FileNotFoundError
```

stack traces in the UI.

---

## Tests

Add tests ensuring:

- no endpoint constructs `/sandboxes/...`
- environment actions resolve runtime-root-aware paths
- sandbox actions work for custom environment names
- missing sandboxes return explicit API errors

Suggested grep checks:

```text
Path("/sandboxes")
"/sandboxes/"
```

---

# Suggested files to audit

- services/control_api/routes/environments.py
- services/control_api/services/environment*
- services/control_api/services/sandbox_manager.py
- services/control_api/runtime_resolver.py
- Environment/SandboxState models
- dashboard environment actions

---

# Acceptance criteria

- custom environments no longer resolve to `/sandboxes/...`
- runtime actions use the configured runtime root
- Redeploy/Stop/Refresh/Delete/View Logs work correctly
- environment metadata stores sandbox ids instead of absolute paths
- missing sandbox errors are user-readable
- no hardcoded `/sandboxes` paths remain
- environment actions work from arbitrary runtime roots
