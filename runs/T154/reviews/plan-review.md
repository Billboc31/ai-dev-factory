# Plan review — T154

Decision: PLAN_APPROVED_WITH_MINOR_FIXES

The plan is focused and generally correct. It keeps the scope limited to Traefik dynamic route readiness and proxy failure classification, without reopening the wider sandbox/deployer lifecycle.

## What is good

- Adds a proxy readiness wait between route registration and healthcheck.
- Separates proxy infrastructure failure from application failure.
- Keeps healthcheck as the authoritative pass/fail step.
- Avoids a broad rewrite of ProxyManager, sandbox cleanup, or Traefik infra.
- Adds targeted tests around readiness and failure classification.

## Required minor fixes

### 1. Do not hardcode the proxy URL format

The plan currently proposes building the URL with:

```text
http://api.sandbox-{sandbox_id}.ai-dev-factory.localhost
```

This should instead reuse the actual registered proxy URL, for example from:

- `proxy_urls["api"]`
- `SANDBOX_API_URL`
- the route registration result

The sandbox domain format must not be duplicated inside `_wait_for_proxy_url()`.

### 2. Test the real Host-routing path

The plan mentions probing:

```text
http://traefik.ai-dev-factory.localhost
```

That is not guaranteed to exist and may not represent the real route path.

The readiness check should validate the real route path, either by requesting the actual pretty URL or by querying `127.0.0.1` with the correct `Host` header derived from `SANDBOX_API_URL`.

### 3. Distinguish route-loaded from backend-healthy

Counting HTTP 502/503 as readiness success can be valid for route readiness, because it proves Traefik received and processed the route.

However, logs and state must distinguish:

```text
proxy route loaded
```

from:

```text
backend healthy
```

Otherwise healthcheck logs become ambiguous.

## Approval condition

Once the plan is adjusted with the above points, it is approved for implementation.
