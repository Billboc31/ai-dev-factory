# T165 — T165 - Environment flows must ensure Traefik infra/bootstrap is running like Deployer

**Source**: GitHub Issue #181

## Description

# T165 - Environment flows must ensure Traefik infra/bootstrap is running like Deployer

## Problem

The Deployer flow correctly ensures Traefik/proxy infrastructure is running before deploying runtimes.

The Environments flow does not.

Observed behavior:

- If Traefik is already running, Environment routes may work.
- If Traefik is stopped/down, creating or starting an Environment does not start Traefik.
- Environment deploy then fails or produces unreachable URLs.
- Healthchecks fail against pretty URLs even though services may be running locally.

This creates inconsistent behavior between:

```text
Deployer
vs
Environment runtime provisioning
```

---

# Goal

Make Environment create/redeploy/start flows reuse the same infra bootstrap behavior as the Deployer.

Environment provisioning must ensure:

- Traefik infra is up
- runtime ingress network exists
- route infrastructure is ready

before route registration and healthchecks.

---

# Required behavior

Before Environment provisioning:

```text
registers routes
runs healthchecks
marks environment ready
```

it must execute the same canonical infra bootstrap logic already used by Deployer.

Expected sequence:

```text
ensure Traefik infra running
→ ensure runtime ingress network exists
→ ensure routes directory/provider ready
→ start runtime/services
→ register routes
→ run healthchecks
```

---

# Required fix

Audit the existing Deployer flow and identify the canonical infrastructure bootstrap entrypoint.

Then reuse that exact logic from:

- Environment create
- Environment redeploy
- Environment start (if separate)

Do NOT duplicate shell commands or reimplement infra startup separately.

---

# Important constraints

Do NOT:

- assume Traefik is already running
- silently skip route registration if Traefik is down
- create a second infra bootstrap implementation
- hardcode container names outside existing infra services
- bypass the deployer/runtime orchestration architecture

Reuse the existing infra lifecycle manager.

---

# Files to audit

- deployer provisioning flow
- infra_service_manager
- traefik_manager
- environment create/start/redeploy flow
- sandbox_manager
- proxy_manager
- route registration lifecycle

---

# Tests

Add/validate tests for:

## Traefik initially stopped

Stop Traefik.

Create environment.

Assert:

- Traefik starts automatically
- runtime ingress network exists
- routes register successfully
- healthchecks succeed

---

## Environment redeploy

Redeploy an environment while infra is stopped.

Assert redeploy restarts infra correctly.

---

## No duplicate bootstrap

Assert repeated environment starts do not create duplicate Traefik stacks/networks.

---

# Acceptance criteria

- Creating an Environment works even when Traefik is initially stopped
- Environment flows ensure Traefik infra exactly like Deployer
- Shared runtime ingress network exists before compose startup
- Routes are registered only after infra is ready
- Healthchecks validate real reachable Traefik URLs
- Existing Deployer behavior remains unchanged
