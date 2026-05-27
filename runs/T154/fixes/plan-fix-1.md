# Plan fix — T154 readiness and proxy classification adjustments

## Objective

Keep the current T154 scope intact while removing a few hardcoded assumptions from the readiness design.

## Required adjustments

### 1. Reuse the actual registered proxy URL

Do not generate proxy URLs manually inside `_wait_for_proxy_url()`.

Avoid:

```text
http://api.sandbox-{sandbox_id}.ai-dev-factory.localhost
```

Instead:

- reuse the registered proxy URL
- reuse `SANDBOX_API_URL`
- or pass the resolved API proxy URL explicitly into `_wait_for_proxy_url()`

This preserves genericity and avoids duplicating domain rules.

## 2. Validate the real Host-routing path

Do not probe a potentially fictive endpoint such as:

```text
http://traefik.ai-dev-factory.localhost
```

Instead:

- probe the actual pretty URL directly
- OR probe `127.0.0.1` while injecting the `Host` header from the sandbox URL

The goal is to validate the same request path used by real sandbox traffic.

## 3. Improve readiness logging semantics

HTTP 502/503 responses may still indicate successful route loading because Traefik received and matched the route.

However, readiness logs should distinguish:

```text
proxy route loaded
```

from:

```text
backend healthy
```

Suggested wording:

```text
proxy: route active (backend not healthy yet)
```

This avoids confusion during runtime debugging.

## Scope unchanged

This fix does NOT change the intended T154 scope:

- no Traefik redesign
- no deploy loop
- no sandbox lifecycle rewrite
- no ProxyManager rewrite
- no auto-fix logic

The ticket remains focused on:

```text
Traefik dynamic route readiness and proxy failure classification
```
