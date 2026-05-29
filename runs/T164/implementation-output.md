All four fixes are clean. Here's what was applied:

**B1 — `sandbox_runtime_deploy.py:389–393`** — Removed `compose_project=state.compose_project,` from the `unregister()` call in the failure cleanup path. No more `TypeError` on failed deployments.

**B2 — `run_sandbox.py`** — Removed `compose_project: str | None = None` parameter from `_unregister_proxy_route()` definition and `compose_project=compose_project` from both the `unregister()` call inside the function and the call site at (now) line 1163. Route files will now be properly removed on sandbox teardown.

**M1 — `sandbox_runtime_deploy.py:284`** — Updated the stale docstring from "Attach Traefik to the compose network and write route file" to "Write route file and register sandbox backends with the proxy".
