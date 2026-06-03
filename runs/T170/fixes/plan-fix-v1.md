# T170 — Plan Fix v1

## Summary

The current T170 plan is acceptable as a compatibility fix, but it should clearly distinguish:

- the preferred compose-managed networking model;
- the fallback runtime repair logic.

## Preferred architecture

Modern compose files should continue to attach `api` and `web` directly to:

- the sandbox default network;
- `ai-dev-factory-runtime`.

The runtime repair logic must not replace compose-managed networking.

## Runtime fallback

The post-compose `docker network connect` logic added in `start.sh` should be documented as:

- a compatibility fallback;
- a repair for older branches/worktrees;
- a safety net when compose configuration is incomplete.

## Validation

After startup, deployment validation should confirm that `api` and `web` are attached to both:

- `sandbox-<id>_default`
- `ai-dev-factory-runtime`

If the attachment still fails, deployment should fail clearly and log the final container networks.

## Logging

When the fallback repair logic is used, add a clear log such as:

```text
start: runtime network attachment repaired for legacy compose config
```
