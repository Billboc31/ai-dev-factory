# T154 — T154 — Stabilize Traefik dynamic route lifecycle

**Source**: GitHub Issue #160

## Description

Goal: make the local Traefik dynamic route lifecycle stable for sandbox validation.

Context:
Sandbox runtime and compose isolation are mostly working, and global Traefik is running. However, proxy URL healthchecks still fail even though route files are registered.

Observed problem:
- Traefik file-provider logs repeated errors for route files that disappear during watcher callbacks.
- This suggests route files are created/deleted too quickly, written non-atomically, or polluted by tests/stale fixtures.

Scope:
- write route files atomically using temp file then rename
- avoid exposing partial files to Traefik
- make route deletion idempotent and safe
- cleanup stale route files for sandboxes that no longer exist
- ensure tests use isolated temporary route directories instead of the real runtime route dir
- after registering a route, verify the proxy URL is actually reachable before healthcheck continues
- classify proxy infrastructure failures separately from application health failures
- never stop or remove global Traefik during sandbox cleanup

Tests:
- atomic route file creation
- idempotent unregister
- stale route cleanup
- tests do not pollute the real route directory
- registered route becomes reachable before proxy healthcheck
- normal sandbox lifecycle does not create missing-file watcher errors

Out of scope:
- HTTPS/TLS
- cloud ingress
- production routing
- replacing Traefik

Acceptance:
- sandbox proxy URLs become reachable after route registration
- Traefik no longer logs missing route file errors during normal sandbox lifecycle
- cleanup removes only the target sandbox route
- stale route files can be pruned safely
- sandbox healthcheck distinguishes proxy infra failure from app failure
- implementation remains generic and project-agnostic
