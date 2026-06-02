# T167 — T167 - Fix Traefik DNS/service discovery by enforcing shared ingress network for all routed containers

**Source**: GitHub Issue #186

## Description

# T167 - Fix Traefik DNS/service discovery by enforcing shared ingress network for all routed containers

## Problem

Traefik routes are registered successfully, but routed backends still fail with:

```text
proxy: route active (backend not healthy yet)
```

and runtime validation often shows:

```text
PASS proxy-infra ... http=502
FAIL api ... no response
FAIL web ... no response
```

Root cause is now strongly suspected to be incorrect Docker networking / service discovery architecture.

Specifically:

- Traefik and routed containers are not consistently attached to the same shared ingress network
- backend aliases may exist only on isolated compose-default networks
- Traefik cannot reliably resolve sandbox backend aliases through Docker DNS
- runtime networking behavior remains inconsistent across deployer/environments/redeploy flows

This is no longer a diagnostics problem.

This ticket must implement the actual networking fix.

---

# Goal

Make Traefik able to reliably resolve and reach every routed backend container through Docker DNS.

All routed containers must share a common ingress network with Traefik.

---

# Required architecture

## Shared ingress network

Introduce or finalize a single shared external Docker network:

```text
ai-dev-factory-runtime
```

This network is the canonical ingress network for:

- Traefik
- api containers
- web containers
- any future routed services

---

## Environment/service attachment

Every routed service must attach to BOTH:

```text
1. its local/default sandbox network
2. ai-dev-factory-runtime
```

Example:

```yaml
services:
  api:
    networks:
      default:
      ai-dev-factory-runtime:
        aliases:
          - sandbox-main-api

  web:
    networks:
      default:
      ai-dev-factory-runtime:
        aliases:
          - sandbox-main-web
```

---

## Traefik attachment

Traefik must also attach to:

```text
ai-dev-factory-runtime
```

and remain attached permanently.

---

## Stable DNS aliases

All backend aliases must be:

- lowercase
- Docker-safe
- deterministic
- derived from the canonical sandbox slug

Example:

```text
sandbox-main-api
sandbox-main-web
```

NOT:

```text
api
web
mixed-case aliases
```

---

# Required implementation work

## 1. Compose generation

Update compose generation so routed services join:

```text
ai-dev-factory-runtime
```

as an external network.

---

## 2. Traefik compose

Ensure Traefik compose permanently joins:

```text
ai-dev-factory-runtime
```

using:

```yaml
external: true
```

Do NOT let compose recreate/manage the runtime network.

---

## 3. Network ownership

`ensure_runtime_network()` becomes the ONLY owner/creator of:

```text
ai-dev-factory-runtime
```

No compose stack may create it independently.

---

## 4. Route backend targets

Generated route files must point to the shared-ingress aliases:

```text
http://sandbox-<slug>-api:8080
http://sandbox-<slug>-web:80
```

not host ports or isolated aliases.

---

## 5. Validation

During deploy validation, verify:

```bash
docker exec <traefik> wget http://sandbox-<slug>-api:8080/health
```

works successfully.

If not:

- fail deployment clearly
- log attached networks and aliases

---

# Important constraints

Do NOT:

- workaround via host.docker.internal
- rely on exposed host ports as primary architecture
- dynamically docker network connect/disconnect after startup as the main solution
- keep isolated compose-default-only networking
- hardcode one environment

The fix must support multiple concurrent environments cleanly.

---

# Acceptance criteria

- Traefik can resolve all backend aliases through Docker DNS
- `docker exec <traefik> wget http://sandbox-<slug>-api:8080/health` succeeds
- Routed environment URLs return real backend responses instead of 502
- Multiple environments work concurrently
- No manual docker network connect commands required
- Runtime ingress networking is deterministic and stable
- Existing deployer and environment flows continue to work
