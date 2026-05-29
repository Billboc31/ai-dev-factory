# T161 — T161 - Fix Environments create flow to provision real sandbox runtime

**Source**: GitHub Issue #172

## Description

# T161 - Fix Environments create flow to provision real sandbox runtime

## Problem

Creating an Environment from the Environments tab displays an environment card in the UI, but does not create the actual sandbox runtime directory.

Example:

Requested environment:

```text
demo-ai-dev-factory
```

Observed behavior:

- environment card appears
- status/actions become available
- no real sandbox directory exists
- later actions fail with:

```text
[Errno 2] No such file or directory: '/sandboxes/demo-ai-dev-factory'
```

The environment metadata exists, but the runtime sandbox was never provisioned.

---

## Root cause hypothesis

The current Create Environment flow likely:

- creates environment metadata only
- persists an environment/sandbox identifier
- displays the environment in the UI
- but never calls the real SandboxManager provisioning/deploy flow

This creates a fake runtime state:

```text
environment exists logically
sandbox does not exist physically
```

---

# Goal

Make Create Environment provision a real runnable sandbox runtime, not only metadata.

Environment creation must go through the same runtime provisioning path used by deploy/sandbox creation flows.

---

# Included

## Real sandbox provisioning

Create Environment must:

- call SandboxManager.create(...)
- create a real sandbox directory under configured runtime root
- write `state.json`
- write `.env`
- initialize runtime directories
- create runtime metadata
- optionally start runtime services
- configure Traefik routes if applicable

---

## Persist real sandbox identifiers

Environment metadata must store the real sandbox id returned by SandboxManager.

Do not derive runtime existence from environment name alone.

---

## Prevent fake runtime states

If sandbox provisioning fails:

- environment creation must fail
- UI must display a clear error
- no fake environment card should remain visible
- no partial runtime metadata should survive

Do not show environments as:

- running
- stopped
- deployable

unless a real sandbox exists.

---

## Runtime validation after create

After environment creation:

Verify:

```text
<runtime_root>/sandboxes/<sandbox_id>/
```

exists and contains:

- `state.json`
- `.env`
- runtime directory

---

## Environment actions validation

After creation:

- Redeploy must work
- Stop must work
- Refresh must work
- Delete must work
- View Logs must work

Actions must use the real sandbox id.

---

## Suggested files to audit

- services/control_api/routes/environments.py
- services/control_api/services/environment*
- services/control_api/services/sandbox_manager.py
- services/control_api/services/deploy*
- environment create handlers
- runtime provisioning flow

---

# Tests

Add tests ensuring:

- creating an environment creates a real sandbox directory
- state.json exists after create
- .env exists after create
- failed provisioning does not leave fake environments
- runtime actions work after create
- sandbox ids come from SandboxManager

---

# Acceptance criteria

- Creating `demo-ai-dev-factory` creates a real sandbox directory
- Runtime files exist after create
- Environment actions work immediately after create
- No environment card survives failed provisioning
- Runtime status reflects real sandbox existence
- Environment metadata references real sandbox ids
- No fake runtime states remain possible
