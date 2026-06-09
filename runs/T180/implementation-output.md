Both fixes are done. Here's a summary:

---

**Fix 1 — `LogViewerDrawer.jsx`**

- Added `BackendDiagnostics` component that renders all previously-ignored `backend_diagnostics` fields:
  - `failure_type` with human-readable labels (Crash loop / DNS/network / Backend app error)
  - `backend_urls` — api and web resolved URLs
  - `traefik_probe` — per-service reachability with green/red coloring
  - `api_container` — status, restarts, health
  - `traefik_networks` — Traefik network membership
- Changed the `.then()` handler to store both `res.data.healthcheck_diagnostics` and `res.data.backend_diagnostics`
- Added `backendDiagnostics` state; passed to `HealthcheckDiagnostics`, rendered via `BackendDiagnostics` below the probe table
- `HealthcheckDiagnostics` now shows when either diagnostics is present (not just healthcheck)

**Fix 2 — `tests/test_parse_healthcheck_output.py`** (new file)

8 unit tests covering: PASS probe parsing, FAIL probe with note, summary line counts, multiple probes, empty stdout, unknown lines ignored, stderr captured, probe without HTTP code. All pass.

**Files modified/created:**
- `apps/dashboard/src/components/runtime-dashboard/LogViewerDrawer.jsx`
- `tests/test_parse_healthcheck_output.py` (new)
