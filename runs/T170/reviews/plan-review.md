# T170 — Plan Review

## Verdict

The current plan is acceptable as a short-term compatibility fix, but it should not be treated as the final networking architecture.

It will likely unblock environments created from worktrees whose `docker-compose.yml` does not attach `api` and `web` to `ai-dev-factory-runtime`.

However, the proposed `docker network connect` post-compose step is a runtime patch. The preferred long-term fix is still to ensure the rendered compose configuration attaches routed services directly to the shared ingress network.

---

## What is correct

The plan identifies the current failure accurately:

- Traefik is attached to `ai-dev-factory-runtime`.
- API/Web containers are only attached to `sandbox-<id>_default`.
- Traefik therefore cannot resolve `sandbox-<id>-api` or `sandbox-<id>-web`.

The proposed post-compose attach step should fix this for old or incomplete compose files.

---

## Main concern

Using `docker network connect` after `docker compose up` means the actual runtime topology is no longer fully described by compose.

This can create drift between:

- `docker compose config`
- the real Docker container network state
- cleanup/stop behavior
- future deploy/redeploy expectations

That is acceptable only if this is explicitly framed as a defensive fallback for legacy branches.

---

## Required clarification

The implementation should treat post-compose `docker network connect` as a fallback, not the primary path.

Preferred order:

1. Render/validate compose config.
2. If compose already declares `ai-dev-factory-runtime`, rely on compose.
3. If containers are not attached after startup, apply `docker network connect` as a compatibility repair.
4. Log clearly that a fallback repair was applied.

---

## Final recommendation

Approve T170 only if the plan is adjusted to say:

- compose-declared networking is the desired model;
- post-compose network connect is a compatibility fallback;
- the deployment must validate final container network state after the fallback;
- future compose templates should keep `api` and `web` attached to `ai-dev-factory-runtime` directly.
