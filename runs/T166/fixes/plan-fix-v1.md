# T166 Plan Fix v1

- Persist backend URLs into validation.json
- Persist normalized backend aliases into validation.json
- Include API/web container runtime state in diagnostics
- Include restart count and health state if available
- Explicitly log Traefik attached Docker networks
- Clarify whether retries apply to backend readiness, route readiness, or both
- Ensure diagnostics distinguish backend crash loops from DNS/network failures
- Keep scope limited to diagnostics and observability
- Do not expand into runtime network redesign or Traefik architecture changes
