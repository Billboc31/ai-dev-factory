# T166 — Plan Review

## Verdict

Plan validated as a strong diagnostic/hardening step.

The proposed changes add:

- actionable Traefik-internal backend diagnostics
- backend alias normalization
- enriched validation.json output
- better healthcheck visibility
- clearer proxy/backend failure distinction

This is valuable because the current logs only report:

```text
proxy: route active (backend not healthy yet)
```

without enough context to identify the actual failing layer.

---

## Strengths

### Good diagnostic coverage

The Traefik-internal `wget` probe is the right approach.

It will clearly distinguish:

- route exists but backend DNS fails
- backend reachable but app unhealthy
- wrong alias/network mismatch
- Traefik network isolation

---

### Correct defensive alias normalization

The `_to_docker_safe_alias()` addition is good defensive hardening.

Docker Compose lowercases many generated names and network identifiers.
Normalizing aliases at the proxy layer avoids subtle DNS mismatches.

---

### Better validation.json observability

Persisting backend diagnostics into validation.json is important for UI/debugging workflows and failed environment persistence.

---

### Healthcheck improvements

Including HTTP codes and increasing retry visibility makes failures significantly easier to diagnose.

---

## Main limitation

This plan is primarily diagnostic.

It explicitly excludes architectural/network fixes:

```text
Fixing any identified root cause that requires a separate architectural change
```

So this ticket should not be considered the final fix for routed backend 502 issues.

A follow-up ticket may still be required depending on what the diagnostics reveal.

Likely future root-cause areas:

- runtime network ownership
- Traefik attachment timing
- alias generation mismatch
- backend startup ordering
- route/backend registration races
- compose network architecture

---

## Recommended additions

### 1. Include route backend URLs in validation.json

Currently planned for logs only.

Also persist:

```json
{
  "backend_urls": {
    "api": "http://...",
    "web": "http://..."
  }
}
```

This will help post-mortem debugging.

---

### 2. Log container status and health

If available, also log:

- container running state
- container health status
- restart count

This will help distinguish:

```text
network issue
vs
backend crash loop
```

---

## Final verdict

Approved as:

```text
Diagnostic + observability + defensive hardening ticket
```

but not sufficient alone to guarantee resolution of the backend 502 problem.
