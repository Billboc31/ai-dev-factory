# T163 — T163 - Persist failed environment deployments for debugging and retry

**Source**: GitHub Issue #176

## Description

# T163 - Persist failed environment deployments for debugging and retry

## Problem

Currently when an Environment deployment/provisioning fails, the environment may disappear entirely or be cleaned too aggressively.

This makes debugging difficult because:

- logs are lost
- runtime metadata disappears
- bootstrap/build/start failure context disappears
- the user cannot inspect the failed environment
- the user cannot retry provisioning from the existing environment card

At the same time, failed environments should still be removable manually.

---

# Goal

Persist failed environment deployments in the dashboard/runtime state so users can:

- inspect logs
- inspect failure reasons
- inspect runtime metadata
- retry deployment
- manually delete the failed environment afterwards

Failed environments should become first-class runtime states instead of disappearing immediately.

---

# Required behavior

## Failed environments remain visible

If provisioning fails during:

- bootstrap
- build
- start
- supervisor startup
- compose startup
- route generation
- healthcheck
- smoke validation

then the environment must remain visible in the UI.

The environment state should become something like:

```text
failed
```

or:

```text
provisioning_failed
```

instead of disappearing.

---

## Preserve failure context

Persist:

- failure reason
- failed lifecycle step
- bootstrap/build/start logs
- supervisor logs
- compose logs
- healthcheck logs
- timestamps
- runtime metadata

This information must remain accessible from the UI.

---

## Retry support

The user must be able to:

```text
Retry Deploy
```

from the failed environment card.

Retry should:

- reuse the same environment metadata
- reuse sandbox path/runtime metadata when safe
- rerun the canonical deploy lifecycle
- update state/logs correctly

---

## Delete support

The existing Delete button must still work for failed environments.

Delete should:

- remove runtime metadata
- remove sandbox/runtime files best-effort
- remove environment card
- cleanup persisted failed state

---

## Avoid fake success states

Failed environments must NOT:

- appear healthy
- appear running
- expose fake working URLs
- expose successful status badges

The UI should clearly indicate failure.

---

# Logs/UI expectations

The failed environment view should expose:

- failure summary
- lifecycle step that failed
- logs grouped by phase:
  - bootstrap
  - build
  - start
  - supervisor
  - healthcheck
  - docker/runtime

Docker logs alone are not sufficient.

---

# Suggested files to audit

- environment runtime state model
- deploy lifecycle persistence
- environment dashboard cards
- logs endpoints
- retry/redeploy flow
- delete flow
- runtime metadata persistence

---

# Acceptance criteria

- Failed environment deployments remain visible in the dashboard
- Failure reason and lifecycle step are persisted
- Logs remain accessible after failure
- Retry Deploy works from failed environments
- Delete works on failed environments
- Failed environments are clearly marked as failed
- No fake healthy/running status is shown
- Existing successful deploy flows continue to work
