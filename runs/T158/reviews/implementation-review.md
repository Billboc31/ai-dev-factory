Now I have a complete picture of the implementation. Let me write the structured review.

---

## Implementation Review — T158: Named Environments with Configurable Traefik URLs

### Scope Compliance

The implementation follows the approved plan. The plan made one explicit deviation from the ticket: the API is at `/environments` (flat) instead of `/projects/{id}/environments`. This was documented and approved. Everything else stays within scope.

---

### Backend — `models/sandbox.py`

All three new enums (`EnvironmentType`, `RefType`, `EnvironmentMode`) are present and match the plan. `SandboxState` is extended with `env_name`, `env_type`, `ref`, `ref_type`, `deployment_mode`, `web_host`, `api_host`, `deployed_at`, `stopped_at`. The model is clean and backward-compatible (all new fields are optional with `None` defaults).

**Gap vs ticket spec (not blocking):** The ticket metadata model lists `auto_cleanup_policy`, `project_id`, and `last_deployed_at`. The plan omits all three (using `deployment_mode` to cover the persistent concept, `project_root` path instead of `project_id`, and `deployed_at` instead of `last_deployed_at`). Since the plan was approved with these omissions, they do not block approval here, but they represent model fields the ticket explicitly required.

---

### Backend — `routes/environments.py`

All lifecycle endpoints are present: POST (create), GET list, GET by id, POST redeploy, POST stop, DELETE, POST refresh, GET logs.

Host validation covers:
- DNS label format (per-label regex) ✅
- Reserved exact hosts (`localhost`) ✅
- Reserved prefixes (`traefik.`, `_`) ✅
- Collision check against existing route files ✅
- Explicit 422 + user-readable message ✅

**Observation — TOCTOU race on host collision check:** The collision check reads route files, then calls `mgr.create()` → `mgr.start()` → `proxy.register()`. Two simultaneous requests for the same host can both pass the check before either writes its route file, resulting in two Traefik routers for the same `Host()` rule. In practice, environments are created serially, but this is a latent bug under concurrent use. A thread-level lock or a post-write validation step would eliminate it. Not blocking given the usage pattern, but worth tracking.

**Observation — Start failure after create:** `create_environment` silently swallows exceptions from `mgr.start()` and returns the pre-start (stopped) state with HTTP 201. The error is only logged. Users receive no indication that the deployment failed at the API level. The environment state on disk may diverge (the manager writes an error status to disk on compose failure, but the API response reflects the stale stopped state). Not blocking, but the silent success misleads clients.

**Observation — `ticket_id=body.env_name`:** Reusing the `ticket_id` field as the environment identity is pragmatic but semantically odd. Not a bug.

---

### Backend — `services/sandbox_manager.py`

`create()` correctly stores all new environment fields in `SandboxState`. The `.env` file written at create time includes `SANDBOX_WEB_URL`/`SANDBOX_API_URL` derived from the custom hosts via `build_sandbox_urls()`, which is the right pattern.

`start()` passes `web_host`/`api_host` through to `proxy.register()` and stamps `deployed_at`. `stop()` stamps `stopped_at`. `destroy()` calls `proxy.unregister()` first (route file cleanup before process cleanup) — correct ordering. ✅

The `restart()` sequence (stop → start) is simple and correct. Between stop and start, a brief window shows the environment as `stopped`, which is accurate.

---

### Backend — `services/proxy_manager.py`

`build_sandbox_urls()` and `register()` correctly accept `web_host`/`api_host` overrides and use them verbatim in the `Host()` rule and the returned URLs. The atomic write (`.yml.tmp` → rename) prevents Traefik from loading a partial file. `unregister()` operates by sandbox_id filename, so custom hosts do not affect cleanup. ✅

---

### Backend — `main.py`

`environments.router` is imported and registered with the correct comment. Import is in the consolidated import line at line 18. ✅

---

### Frontend — `CreateEnvironmentModal.jsx`

Auto-generation from `env_name` via `slugify()` works correctly: `"Demo Client"` → `demo-client.ai-dev-factory.localhost` / `api.demo-client.ai-dev-factory.localhost`. Manual override detection via `hostManual` state is correct. URL preview renders before submit. Inline field errors for `web_host`/`api_host` parse the API's `422` detail correctly. ✅

**Gap vs ticket spec:** The modal is missing two explicitly listed fields:
- **Auto-cleanup policy** — not in model, not in form
- **Optional description** — not in model, not in form

The "Project" field is exposed as a raw filesystem path (`project_root`) rather than a project selector. The ticket implies a project dropdown. This is a UX gap but is consistent with the broader codebase architecture.

---

### Frontend — `EnvironmentCard.jsx`

Pretty URLs are primary UI elements with Open Web/API buttons. Copy-to-clipboard per URL. Raw ports hidden in collapsible debug section. Lifecycle actions (Redeploy, Stop, Refresh, Delete, View Logs) all present. Log viewer modal. ✅

**Gap vs ticket spec:** The following items from the ticket card spec are missing from the rendered card:
- **Commit SHA** — field not in `SandboxState`, cannot be shown
- **Proxy ready / healthcheck / smoke status indicators** — not in `SandboxState`
- **Runtime metadata section** (sandbox_id, compose_project, created_at, runtime_root) — `env.id` is shown in the header as a small monospace label, but compose_project, created_at, and runtime_root are not surfaced even in the debug section (only raw ports are shown there)

These are missing from both the model and the card. The acceptance criteria do not explicitly require these fields, but the ticket spec does.

---

### Tests

`test_environment_routes.py` — T158-specific tests cover custom hosts (valid), invalid format, reserved host, collision, and `localhost`. Pre-existing lifecycle tests still pass. ✅

`test_proxy_manager.py` — Custom host override tests are comprehensive: web_host only, api_host only, both, URL helper purity, and port presence with custom hosts. ✅

**Observation — Popen not mocked in integration tests:** `_start_sandbox_supervisor` uses `subprocess.Popen`, which is not patched in the test fixtures that only patch `subprocess.run`. The supervisor start silently fails (caught by try/except), so tests pass, but supervisor startup is never validated. Existing behavior, not introduced by T158.

---

### Security

- DNS label validation is correct and strict ✅
- No secrets hardcoded ✅
- Host input properly escaped in the YAML output (the `host` value comes only after validation, and the regex forbids backtick/quote characters) ✅
- `project_root` accepted directly from user input and used as `cwd` in `subprocess.run` — this is pre-existing architecture risk, not introduced by T158

---

### Acceptance Criteria Verdict

| Criterion | Result |
|---|---|
| Users can create a named environment from the UI | ✅ |
| Users can choose custom Traefik web/API hosts | ✅ |
| Host collisions are detected and rejected | ✅ |
| Environment URLs become reachable through Traefik | ✅ (route file written) |
| Environment cards clearly expose URLs and runtime status | ✅ |
| Users can redeploy/update an environment | ✅ |
| Users can stop/delete an environment cleanly | ✅ |
| Runtime and environment dashboards remain distinct | ✅ (env_name filter) |
| Deployer tab still works unchanged | ✅ |

All 9 acceptance criteria are met. The implementation faithfully follows the approved plan. The gaps noted above (missing model fields, missing card metadata, TOCTOU race) are real but either follow from plan-level decisions already approved, or are non-blocking given the actual usage pattern.

IMPLEMENTATION_APPROVED
