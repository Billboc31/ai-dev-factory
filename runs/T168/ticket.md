# T168 — T168 - Fix SANDBOX_ID mismatch between Traefik backend routes and Docker Compose aliases

**Source**: GitHub Issue #188

## Description

# T168 - Fix SANDBOX_ID mismatch between Traefik backend routes and Docker Compose aliases

## Problem

Traefik networking and shared ingress network are now functioning correctly.

Verified:

- Traefik and backend containers are attached to `ai-dev-factory-runtime`
- Docker DNS resolution works between containers
- Backend API is reachable directly from Traefik container

Example:

```bash
docker exec ai-dev-factory-infra-traefik-1 wget http://ai-dev-factory-api-1:8080/health
```

returns HTTP 200 successfully.

However routed URLs still fail because the generated Traefik backend alias does not match the alias actually created by Docker Compose.

Observed mismatch:

```text
Route backend target:
sandbox-main-api

Actual Docker alias:
sandbox-default-api
```

Result:

```text
wget: bad address 'sandbox-main-api:8080'
```

This proves the shared ingress network works, but SANDBOX_ID propagation is inconsistent between:

- route generation
- compose alias generation
- environment deploy flow

---

# Root cause

Traefik routes are generated using the selected environment/sandbox id:

```text
main
```

but Docker Compose starts services with fallback:

```text
SANDBOX_ID=default
```

So generated aliases become:

```text
sandbox-default-api
sandbox-default-web
```

instead of:

```text
sandbox-main-api
sandbox-main-web
```

Traefik therefore routes to aliases that do not exist.

---

# Goal

Ensure one canonical sandbox/environment slug is used consistently across:

- docker compose env vars
- compose network aliases
- Traefik backend URLs
- validation probes
- runtime state
- deploy flows

---

# Required fixes

## 1. Canonical sandbox/env slug

Introduce or reuse a single canonical sandbox/env slug.

This slug must be propagated everywhere.

Example:

```text
main
```

must consistently produce:

```text
sandbox-main-api
sandbox-main-web
```

---

## 2. Docker compose SANDBOX_ID propagation

Ensure compose is launched with the real sandbox/env id:

```bash
SANDBOX_ID=main docker compose up -d
```

Do NOT silently fallback to:

```text
SANDBOX_ID=default
```

for named environments.

---

## 3. Fail fast when SANDBOX_ID missing

Before compose startup:

- validate SANDBOX_ID exists
- validate it matches runtime state
- validate route generation uses the same value

Deployment must fail explicitly if values diverge.

---

## 4. Route generation alignment

Generated Traefik backend URLs must use the same canonical slug used by compose aliases.

---

## 5. Validation

Deployment validation must verify:

```bash
docker exec <traefik> wget http://sandbox-<slug>-api:8080/health
```

using the canonical slug.

---

# Suggested files to audit

- docker compose generation
- environment deploy flow
- sandbox_runtime_deploy.py
- run_sandbox.py
- proxy_manager.py
- proxy_network.py
- route generation logic
- runtime state persistence
- compose env injection

---

# Acceptance criteria

- `docker inspect <api>` shows alias `sandbox-main-api` for environment `main`
- Generated route file points to `sandbox-main-api`
- `docker exec <traefik> wget http://sandbox-main-api:8080/health` succeeds
- No `sandbox-default-*` aliases appear unless env id is actually `default`
- Traefik routed URLs return real backend responses instead of 502
- Multiple environments continue to work concurrently
- Deployments fail early if SANDBOX_ID propagation is inconsistent
