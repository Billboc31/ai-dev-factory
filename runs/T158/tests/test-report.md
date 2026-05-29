Now let me write the test report.

---

## Test Report — T158: Named Environments with Configurable Traefik URLs

### Methodology

- Read all implementation files changed vs `main`
- Ran targeted test suites (environment routes, proxy manager, deployer, sandbox manager)
- Ran full suite (1107 passing tests, excluding `tests/supervisor/`) to check for regressions
- Verified all failures against `main` clone to identify pre-existing failures
- Reviewed frontend components against acceptance criteria manually

---

### Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Users can create a named environment from the UI | **PASS** |
| 2 | Users can choose custom Traefik web/API hosts | **PASS** |
| 3 | Host collisions are detected and rejected | **PASS** |
| 4 | Environment URLs become reachable through Traefik | **PARTIAL** ¹ |
| 5 | Environment cards clearly expose URLs and runtime status | **PASS** |
| 6 | Users can redeploy/update an environment | **PASS** |
| 7 | Users can stop/delete an environment cleanly | **PASS** |
| 8 | Runtime dashboard and environment dashboard remain distinct | **PASS** |
| 9 | Deployer tab still works unchanged for quick validation | **PASS** |

¹ Route files are written correctly with custom `Host(...)` rules (verified by proxy manager tests), but live Traefik reachability cannot be confirmed in the test environment — that requires a running Docker/Traefik stack.

---

### Detailed Findings

**Criterion 1 — Create named environment from UI**
`CreateEnvironmentModal.jsx` provides `env_name`, `project_root`, `ref`, `ref_type`, `env_type`, and deployment mode fields. `POST /environments` returns 201 with metadata. Tests `test_deploy_branch_environment` and `test_deploy_persistent_environment` pass.

**Criterion 2 — Custom Traefik hosts**
Modal has `web_host` / `api_host` fields. `handleEnvNameChange()` auto-generates slugified hosts (e.g., `"Demo Client"` → `demo-client.ai-dev-factory.localhost` / `api.demo-client.ai-dev-factory.localhost`). Manual edits disable auto-generation per field. The API client in `environments.js` forwards both host fields. `test_create_environment_with_custom_hosts` confirms the API returns the exact provided hosts and the correct `http://` URLs.

**Criterion 3 — Host collision detection**
`_declared_hosts()` scans all `proxy/routes/*.yml` files for `Host(...)` rules. A second environment claiming an already-registered host receives HTTP 422 with `web_host: host already in use: ...`. DNS-unsafe formats (e.g., `"my host!.localhost"`) and reserved prefixes (`traefik.*`, `localhost`) are also rejected with 422. The modal parses these errors and renders them inline beneath the affected field. Tests `test_create_environment_host_collision`, `test_create_environment_invalid_host_format`, `test_create_environment_reserved_host`, `test_create_environment_localhost_reserved` all pass.

**Criterion 4 — Traefik reachability (partial)**
`ProxyManager.register()` and `build_sandbox_urls()` accept `web_host`/`api_host` overrides and write them verbatim into the Traefik route YAML as `Host(...)` rules. `SandboxManager.create()` stores custom hosts in `SandboxState` and passes them to the proxy manager on `start()`/`restart()`. Tests `test_register_with_custom_web_host`, `test_register_with_both_custom_hosts`, `test_build_sandbox_urls_with_custom_hosts` verify correct route file content. Live DNS routing via Traefik cannot be confirmed without a running Docker stack.

**Criterion 5 — Environment card URLs and status**
`EnvironmentCard.jsx` renders `env.urls.web` and `env.urls.api` as primary `<a>` links ("Open Web ↗" / "Open API ↗") with copy buttons. Status, env_type, and deployment_mode are shown as color-coded badges. Raw port numbers are hidden under a collapsible "Debug" toggle (`showDebug` defaults to `false`).

**Criterion 6 — Redeploy**
`POST /environments/{id}/redeploy` delegates to `SandboxManager.restart()`. "Redeploy" action button present in the card.

**Criterion 7 — Stop / Delete cleanly**
`POST /environments/{id}/stop` sets status to `stopped` and `stopped_at` timestamp (`test_environment_lifecycle_transitions` passes, idempotency also confirmed). `DELETE /environments/{id}` removes the sandbox directory, unregisters the proxy route file, and returns 204; subsequent `GET` returns 404 (`test_environment_deletion_cleanup` passes).

**Criterion 8 — Distinct responsibilities**
`GET /environments` filters with `env_name is not None`, keeping environments separate from raw sandboxes. Runtime dashboard and sandbox APIs are untouched.

**Criterion 9 — Deployer tab unchanged**
The only change to `deployer.py` is removal of three unused imports (`Body`, `BaseModel`, `SandboxManager`) — no functional change. All 5 deployer route tests pass.

---

### Regression Check

- **71 T158-related tests**: 71/71 pass
- **Full suite (1107 tests)**: 1107 pass, 46 fail — all 46 failures confirmed pre-existing on `main` (verified by running against the main clone). Failing suites: `test_control_api_artifacts`, `test_control_api_endpoints`, `test_control_api_subprocess`, `test_daemon_checkpoint`, `test_daemon_issue_polling`, `test_run_daemon`, `test_ticket_timeline`, `tests/supervisor/`.

---

### Verdict

**PASS** — all verifiable acceptance criteria are satisfied. No regressions introduced. The one non-verifiable criterion (live Traefik reachability) has correct infrastructure in place; it only requires a running Docker/Traefik stack to confirm end-to-end.
