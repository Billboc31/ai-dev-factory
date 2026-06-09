# T180 — T180 - Healthcheck failure logs must prioritize actionable Traefik and proxy diagnostics

**Source**: GitHub Issue #212

## Description

## Problem

Environment deploy failures are now mostly caused by `healthcheck.sh`, but the current logs UI does not surface actionable diagnostics first.

Even with the new Full Logs proposal, users would still need to manually inspect a large raw log dump to understand proxy/routing failures.

The most common current failures are related to:

- Traefik routing
- proxy/backend connectivity
- incorrect runtime URLs
- healthcheck endpoint failures
- container/network resolution

---

## Goal

When `failing_step=healthcheck.sh`, the logs UI must prioritize actionable diagnostics before the raw logs.

The raw full logs should still remain available.

---

## Required UI behavior

Add a dedicated "Failure details" section above the raw logs.

When the failing step is `healthcheck.sh`, surface:

- tested URLs
- HTTP status codes
- curl/wget stdout/stderr
- resolved backend URL
- Traefik route diagnostics
- backend container status
- network diagnostics
- validation.json failure_type
- healthcheck exit code

---

## Required backend behavior

Expose structured healthcheck diagnostics from:

- validation.json
- healthcheck stdout/stderr
- runtime proxy diagnostics

Prefer structured fields over raw text parsing when possible.

---

## Important constraint

Do not remove the raw Full Logs view.

The diagnostics section should augment the logs, not replace them.

---

## Acceptance criteria

- Healthcheck failures surface actionable diagnostics immediately
- Traefik/proxy routing issues are visible without opening raw logs
- Tested URLs and HTTP codes are displayed clearly
- validation.json diagnostics are surfaced in the UI
- Raw full logs are still accessible
- Existing step summary behavior remains unchanged
