# T164 — T164 - Replace Docker Compose v2.5-style environment networking with robust shared runtime network architecture

**Source**: GitHub Issue #179

## Description

# T164 - Replace Docker Compose v2.5-style environment networking with robust shared runtime network architecture

## Problem

The current dynamic Environment deployment/networking architecture behaves like an old Docker Compose v2.5-era setup:

- isolated per-compose default networks
- fragile dynamic network attachment
- Traefik not reliably attached to runtime networks
- service discovery instability
- broken dynamic route loading
- environment URLs failing despite containers running
- repeated runtime networking regressions

Observed symptoms:

- Traefik cannot resolve `api` / `web`
- environments start but URLs fail
- manual `docker network connect` debugging needed
- route/provider instability
- dynamic environment networking feels bolted-on instead of designed for multi-env runtime orchestration

Current state strongly suggests the architecture evolved from:

```text
single compose stack
```

instead of:

```text
multi-runtime environment orchestration platform
```

---

# Goal

Redesign Environment runtime networking around a proper shared runtime network architecture suitable for:

- multiple dynamic environments
- dynamic Traefik routing
- supervisor-managed runtimes
- reusable deploy pipelines
- runtime service discovery
- stable environment URLs

without relying on fragile compose-default isolated networks.

---

# High-level direction

Move from:

```text
one isolated compose network per environment
```

Toward:

```text
shared runtime ingress network
+ optional per-env internal networks
+ stable service discovery model
```

Traefik must always have deterministic access to runtime services.

---

# Required architecture audit

Audit current:

- compose generation
- network generation
- Traefik integration
- runtime service discovery
- route generation
- supervisor/runtime orchestration
- healthcheck assumptions
- deployer vs environments networking differences

Document:

- where networks are created
- who owns ingress networking
- how Traefik discovers services
- why dynamic env networking is unstable
- whether compose defaults are relied upon implicitly

---

# Desired target model

Example target architecture:

```text
shared ingress network
  ↕
Traefik
  ↕
environment services
```

Optional:

```text
shared ingress network
+ per-environment private network
```

But ingress connectivity must always be deterministic.

---

# Requirements

## Stable networking

Environment URLs must work immediately after successful deploy.

No manual:

```bash
docker network connect
```

must ever be required.

---

## Stable service discovery

Traefik must always be able to resolve backend services.

Avoid reliance on:

- compose-generated unstable network names
- accidental aliases
- timing-dependent attach behavior
- temporary dynamic network mutation

---

## Generic architecture

The solution must work for:

- multiple projects
- multiple environments
- concurrent runtimes
- custom sandbox paths
- future scaling of the runtime platform

Do NOT hardcode:

- one network name
- one project
- one compose stack

---

## Runtime ownership clarity

Clearly define ownership for:

- ingress network
- environment internal networks
- route generation
- Traefik registration
- runtime cleanup
- supervisor/runtime lifecycle

---

# Important constraints

Do NOT:

- patch around issues with repeated `docker network connect`
- hardcode network attachment everywhere
- bypass Traefik
- expose only host ports as primary architecture
- keep layering fixes on top of fragile compose-default networking

The goal is a proper runtime networking model.

---

# Suggested implementation directions

Potential approaches to evaluate:

- shared ingress network
- explicit external networks in compose generation
- deterministic network naming
- runtime network registry
- Traefik service discovery via labels instead of file-only routing
- supervisor-managed runtime attachment
- network lifecycle abstraction

---

# Tests

Add/validate:

## Multiple environments

Deploy multiple environments concurrently.

Assert:

- all URLs reachable
- no network conflicts
- Traefik reaches all envs

---

## Redeploy stability

Redeploy environments repeatedly.

Assert:

- routes remain valid
- no watcher/network races
- no orphaned networks

---

## Cleanup

Delete environment.

Assert:

- routes removed cleanly
- networks cleaned correctly
- other envs unaffected

---

# Acceptance criteria

- Dynamic environments work reliably through Traefik
- No manual network attach/debugging required
- Traefik consistently resolves environment services
- Networking architecture supports multiple concurrent environments
- Runtime networking ownership is clearly defined
- Compose-generated default-network fragility is eliminated
- Existing deployer/runtime flows continue functioning
