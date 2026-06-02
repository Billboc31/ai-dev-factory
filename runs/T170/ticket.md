# T170 — T170 - Attach API/Web services to shared runtime network in environment compose flow

**Source**: GitHub Issue #192

## Description

# T170 - Attach API/Web services to shared runtime network in environment compose flow

## Problem

After fixing SANDBOX_ID propagation, routes now target the expected aliases:

```text
sandbox-d966c3e9f1c9-api
sandbox-d966c3e9f1c9-web
```

but Traefik still cannot resolve them:

```text
proxy: backend probe api=failed: wget: bad address 'sandbox-d966c3e9f1c9-api:8080'
proxy: backend probe web=failed: wget: bad address 'sandbox-d966c3e9f1c9-web:80'
```

Diagnostics show the actual remaining problem:

```text
traefik container networks=['ai-dev-factory-infra_default', 'ai-dev-factory-runtime']
api container networks=['sandbox-d966c3e9f1c9_default']
```

So Traefik is correctly attached to `ai-dev-factory-runtime`, but API/Web containers are not.

This means Docker DNS cannot resolve the routed aliases from the Traefik container.

---

# Goal

Ensure every routed service container (`api`, `web`) joins both:

```text
1. its sandbox default/internal network
2. ai-dev-factory-runtime shared ingress network
```

with the correct canonical aliases.

---

# Required fix

Update the compose generation / compose template used by the environment deploy flow so routed services are attached to the shared runtime network.

Expected rendered compose shape:

```yaml
services:
  api:
    networks:
      default: {}
      ai-dev-factory-runtime:
        aliases:
          - sandbox-${SANDBOX_ID}-api

  web:
    networks:
      default: {}
      ai-dev-factory-runtime:
        aliases:
          - sandbox-${SANDBOX_ID}-web

networks:
  ai-dev-factory-runtime:
    external: true
    name: ai-dev-factory-runtime
```

The aliases must use the same canonical SANDBOX_ID/slug used by route generation.

---

# Important distinction

This is NOT a SANDBOX_ID problem anymore.

SANDBOX_ID now appears correct in route generation.

The remaining failure is that containers are only attached to:

```text
sandbox-<id>_default
```

and not to:

```text
ai-dev-factory-runtime
```

---

# Validation commands

After fix, this must show both networks:

```bash
docker inspect <api-container> --format '{{json .NetworkSettings.Networks}}' | jq 'keys'
```

Expected:

```json
[
  "ai-dev-factory-runtime",
  "sandbox-<id>_default"
]
```

This must succeed:

```bash
docker exec <traefik-container> wget http://sandbox-<id>-api:8080/health
```

---

# Suggested files to audit

- docker-compose.yml
- compose generation code
- `.ai-dev-factory/scripts/start.sh`
- `services/control_api/services/sandbox_runtime_deploy.py`
- `services/control_api/services/sandbox_manager.py`
- any environment-specific compose template or runtime overlay

---

# Acceptance criteria

- API container is attached to `ai-dev-factory-runtime`
- Web container is attached to `ai-dev-factory-runtime`
- API/Web also keep their sandbox default/internal network
- Runtime aliases exist on `ai-dev-factory-runtime`
- Traefik resolves `sandbox-<id>-api` and `sandbox-<id>-web`
- `docker exec <traefik> wget http://sandbox-<id>-api:8080/health` returns HTTP 200
- Routed URLs no longer return 502 due to DNS/network failure
- Multiple environments can coexist without alias collisions
