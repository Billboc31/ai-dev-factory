# T166 — T166 - Diagnose and fix routed backend 502 after route registration

**Source**: GitHub Issue #184

## Description

# T166 - Diagnose and fix routed backend 502 after route registration

## Problem

A sandbox/environment deployment can reach the Traefik route, but the backend never becomes healthy.

Observed output:

```text
proxy: route active (backend not healthy yet)
resolved script path: /Users/pierrebocquet/ai-dev-factory/.ai-dev-factory/scripts/healthcheck.sh

--- healthcheck.sh (.ai-dev-factory/scripts/healthcheck.sh) ---
PASS  proxy-infra  (http://api.main.ai-dev-factory.localhost)  — route reachable, http=502
FAIL  api  (http://api.main.ai-dev-factory.localhost/health)  — no response after 3 attempts
FAIL  web  (http://main.ai-dev-factory.localhost)  — no response after 3 attempts
PASS  supervisor  (http://127.0.0.1:8094/health)

healthcheck: 2 passed, 2 failed
healthcheck: sandbox=cf23c1149f36
validation.json written to /Users/pierrebocquet/environment/main/runtime/validation.json
```

This means Traefik has a matching route, but the upstream service is unavailable, unreachable, or misconfigured.

---

# Goal

Diagnose and fix the remaining routed-backend failure where Traefik returns 502 after a route is registered.

The fix must determine whether the issue is caused by:

- containers not running
- app process not healthy
- wrong backend URL in route file
- Docker DNS alias mismatch
- Traefik not attached to the correct runtime network
- route file pointing to stale sandbox/service names
- healthcheck running before backend readiness
- sandbox id / slug mismatch
- compose project casing mismatch
- wrong port mapping / wrong internal service port

---

# Included

## 1. Add diagnostic logging around proxy validation

When proxy validation returns 502 or route-active-but-backend-unhealthy, log:

- sandbox id
- Docker-safe sandbox slug
- compose project name
- route file path
- route backend URLs
- expected API alias
- expected web alias
- Traefik container name
- Traefik networks
- app container names
- app container networks
- API/web container status
- direct container health result if available

Do not just report `backend not healthy yet`.

---

## 2. Validate backend reachability from Traefik container

During validation, run or implement the equivalent of:

```bash
docker exec <traefik-container> wget -S -O- http://<api-backend-alias>:8080/health
docker exec <traefik-container> wget -S -O- http://<web-backend-alias>:80
```

Use this to distinguish:

```text
route exists but upstream DNS/connection fails
```

from:

```text
upstream reachable but app health fails
```

---

## 3. Verify route file backend URLs

Generated route files must point to the canonical Docker-safe aliases, for example:

```text
http://sandbox-<slug>-api:8080
http://sandbox-<slug>-web:80
```

They must not point to:

```text
http://api:8080
http://web:80
http://host.docker.internal:<port>
```

unless this is explicitly the selected architecture.

---

## 4. Normalize sandbox ids for Docker DNS

If sandbox ids can contain uppercase characters or timestamp separators, ensure all Docker DNS aliases and route backend URLs use the same canonical lowercase Docker-safe slug.

Example:

```text
ai-dev-factory-20260601T194957
```

must produce backend aliases like:

```text
sandbox-ai-dev-factory-20260601t194957-api
sandbox-ai-dev-factory-20260601t194957-web
```

not mixed-case variants.

---

## 5. Improve healthcheck timing and readiness reporting

If the backend is still starting:

- retry long enough for normal API/web startup
- report the exact failing phase
- persist failure diagnostics in `validation.json`

Do not mark a route as healthy only because Traefik returns any response.

---

# Suggested files to audit

- `.ai-dev-factory/scripts/healthcheck.sh`
- `.ai-dev-factory/scripts/start.sh`
- proxy validation logic
- route generation logic
- `proxy_manager.py`
- `proxy_network.py`
- `sandbox_runtime_deploy.py`
- Docker compose generation / network aliases
- validation.json writer

---

# Acceptance criteria

- A route returning 502 produces actionable diagnostics, not only `backend not healthy yet`
- Backend aliases in route files are canonical and Docker-safe
- Traefik can resolve and reach the generated backend aliases
- Healthcheck distinguishes route reachable from backend healthy
- `validation.json` contains route backend diagnostics when validation fails
- Once API/web containers are running and healthy, routed URLs pass:

```text
http://api.<env>.ai-dev-factory.localhost/health
http://<env>.ai-dev-factory.localhost
```

- Existing successful deployer and environment flows continue to work
