All changes are implemented and verified. Here's the summary:

---

## Files modified

**`.ai-dev-factory/scripts/start.sh`** — Primary fix  
Inserted a runtime network attachment block after `docker compose up -d`. For each sandbox service (`api`, `web`):
- Queries the container ID via `docker compose ps -q`
- Checks if already on `ai-dev-factory-runtime` via `docker inspect`
- If missing: runs `docker network connect --alias sandbox-${SANDBOX_ID}-<svc>`
- Handles the "already connected" race-condition error idempotently
- Post-attachment validation: exits with a clear error if the service still isn't on the network after the connect attempt
- Logs `"start: runtime network attachment repaired for legacy compose config"` when the fallback fires

**`services/control_api/services/sandbox_manager.py`** — Defensive fix  
Added `ensure_runtime_network` to the import and called it at the top of `SandboxManager.start()`, before `_run_compose`. This prevents a hard failure when the worktree's compose file declares `ai-dev-factory-runtime` as `external: true` but the network hasn't been created yet.

---

## Files created

**`tests/test_start_sh_network_attach.py`** — 3 tests covering:
1. Containers not on runtime network → `docker network connect` called with correct alias for both api and web
2. Containers already on runtime network → connect not called (idempotent)
3. Connect returns "already exists" error → treated as idempotent, deploy succeeds

**`tests/test_sandbox_manager.py`** — 1 new test added  
`test_start_calls_ensure_runtime_network_before_compose_up`: verifies `ensure_runtime_network()` is called before `docker compose up` in `SandboxManager.start()`.
