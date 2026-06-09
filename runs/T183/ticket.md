# T183 — T183 — Fix manual deployment healthcheck failure: proxy route active but backend unhealthy

**Source**: GitHub Issue #183

## Description

## Problem

Manual deployment reaches the proxy layer, but API and web healthchecks fail.

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

## Current interpretation

Traefik/proxy routing appears to exist, because `proxy-infra` passes and returns HTTP 502. However, the backend service behind the route is not healthy or not reachable.

The supervisor is healthy, so the failure is likely in one of these areas:

- API container not running or exiting immediately
- web container not running or exiting immediately
- missing/incorrect runtime env vars in manual deployment
- manual deployment not reproducing deployer startup orchestration
- Traefik points to the wrong internal service/port/network
- healthcheck runs before API/web readiness and does not wait long enough

## Investigation checklist

Compare manual deployment against deployer-managed deployment:

```bash
docker ps -a
docker logs <api-container> --tail=200
docker logs <web-container> --tail=200
docker inspect <api-container>
docker inspect <web-container>
docker logs traefik --tail=200
```

Focus on:

- container state / exit code
- entrypoint and cmd
- env vars
- working directory
- networks
- Traefik labels
- `loadbalancer.server.port`
- router/service naming uniqueness
- healthcheck timing and retry strategy

## Expected fix

Manual deployment should produce the same runtime behavior as deployer deployment:

- `http://api.main.ai-dev-factory.localhost/health` responds successfully
- `http://main.ai-dev-factory.localhost` responds successfully
- API and web containers stay running
- `healthcheck.sh` reports all checks passing
- `validation.json` clearly explains failures when a service is unhealthy

## Acceptance criteria

- Manual deployment no longer ends with `backend not healthy yet`
- Proxy route does not stay at HTTP 502 once startup completes
- API healthcheck passes after startup
- Web healthcheck passes after startup
- If API/web crash, healthcheck output includes actionable logs or container status
- Deployer-managed deployment remains unchanged and working
