## Review complete — IMPLEMENTATION_FIX_REQUIRED

The implementation correctly identifies what was pre-existing (atomic writes, idempotent unregister, stale cleanup) and adds the two genuinely missing pieces: proxy readiness wait and infra failure classification. The logic and test structure are sound.

However, the code was written against the original draft plan rather than the approved plan, which carried three required fix conditions. None were applied:

1. **`run_sandbox.py:285`** — `_wait_for_proxy_url()` hardcodes `http://api.sandbox-{sandbox_id}.ai-dev-factory.localhost` instead of accepting the registered URL from `_register_proxy_route()`'s return value. Explicitly rejected by the plan reviewer; violates the "generic and project-agnostic" acceptance criterion.

2. **`healthcheck.sh:74`** — Probes `http://traefik.ai-dev-factory.localhost` (Traefik dashboard, a fictive endpoint) instead of `$SANDBOX_API_URL`. This validates only that Traefik is up, not that the specific sandbox route is loaded. The plan reviewer required probing the actual route path.

3. **`run_sandbox.py:289,293`** — Both HTTP 200 and HTTP 4xx/5xx responses log identical `"proxy: route active"`, making "backend healthy" indistinguishable from "route loaded, backend not ready" in logs. The plan reviewer specifically required this distinction.

All three fixes are small and targeted — no structural redesign needed. Full review is at `runs/T154/reviews/implementation-review.md`.
