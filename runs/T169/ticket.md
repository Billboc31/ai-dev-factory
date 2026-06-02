# T169 — T169 - Fix Docker Compose env interpolation ignoring runtime SANDBOX_ID and falling back to default aliases

**Source**: GitHub Issue #190

## Description

# T169 - Fix Docker Compose env interpolation ignoring runtime SANDBOX_ID and falling back to default aliases

## Problem

T168 identified the SANDBOX_ID mismatch between:

- Traefik backend routes
- Docker Compose-generated aliases

However additional debugging now proves the issue is deeper:

```bash
docker compose config | grep sandbox-
```

returns:

```text
sandbox-default-api
sandbox-default-web
```

instead of the expected:

```text
sandbox-main-api
sandbox-main-web
```

This means Docker Compose interpolation itself is not receiving the expected runtime SANDBOX_ID value.

The deploy/runtime flow may export SANDBOX_ID in the shell, but the actual compose interpolation context still falls back to:

```text
${SANDBOX_ID:-default}
```

resulting in broken Traefik routing and DNS resolution.

---

# Root cause hypothesis

One or more of the following is happening:

- `docker compose --env-file deploy/.env` overrides runtime shell env
- compose interpolation occurs before runtime export
- deploy/.env does not contain SANDBOX_ID
- compose subprocess does not inherit shell env correctly
- another compose include/file resets the variable
- runtime worker launches compose with a clean environment

---

# Goal

Make Docker Compose interpolation deterministic and fully driven by the canonical runtime environment id.

Compose config generation itself must produce:

```text
sandbox-main-api
sandbox-main-web
```

before any container starts.

---

# Required fixes

## 1. Generate explicit runtime compose env file

Generate a dedicated runtime env file before compose execution.

Example:

```text
runtime/.env.compose
```

containing:

```env
SANDBOX_ID=main
```

This file becomes the canonical compose interpolation source.

---

## 2. Compose invocation order

Launch compose with deterministic env-file precedence.

Example:

```bash
docker compose \
  --env-file deploy/.env \
  --env-file runtime/.env.compose \
  up -d
```

The runtime env file must override defaults.

---

## 3. Remove reliance on inherited shell env

Do NOT rely on:

```bash
export SANDBOX_ID=...
```

as the primary propagation mechanism.

The worker/deployer/runtime system is too complex and subprocess inheritance is unreliable.

Explicit compose env files must be the source of truth.

---

## 4. Validation before compose up

Before compose startup:

```bash
docker compose config
```

must already contain:

```text
sandbox-main-api
sandbox-main-web
```

If config still resolves to `sandbox-default-*`, fail deployment immediately.

---

## 5. Add runtime diagnostics

Log:

- resolved compose env files
- final SANDBOX_ID value
- `docker compose config` alias snippet
- effective compose project name

This should make future env interpolation issues trivial to diagnose.

---

# Acceptance criteria

- `docker compose config | grep sandbox-` shows sandbox-main aliases for env `main`
- `docker inspect <api>` shows alias `sandbox-main-api`
- Traefik can resolve sandbox-main-api through Docker DNS
- Routed URLs no longer return 502
- No fallback to `sandbox-default-*` occurs unless env id is actually `default`
- Deployments fail early if compose interpolation resolves incorrectly
- Multiple environments continue to work concurrently and deterministically
