---

## Test Report — T140

**Verdict: TEST_COMPLETE — PASS**

All 7 acceptance criteria pass.

| Criterion | Status |
|-----------|--------|
| Sandbox UI no longer displays main runtime state | **PASS** |
| Sandbox API communicates only with sandbox supervisor | **PASS** |
| Each sandbox has its own runtime root | **PASS** |
| Each sandbox has its own supervisor instance | **PASS** |
| Multiple sandboxes run simultaneously without collisions | **PASS** |
| Sandbox cleanup does not affect main runtime | **PASS** |
| Logs, state, proposals isolated per sandbox runtime | **PASS** |

**Test counts:**
- 12 new isolation tests (`test_sandbox_isolation.py`) — all pass
- 35 existing sandbox tests (manager / routes / supervisor) — all pass
- Full suite: 888 passed, 45 failed — identical failure set to `main`, zero regressions

**Key implementation verified:**
- `SandboxState` carries `supervisor_port` and `sandbox_runtime_root` per sandbox (`sandbox.py:26–27`)
- `create()` allocates `supervisor_port = 8090 + slot` and an isolated runtime root (`sandbox_manager.py:133–138`)
- `_start_sandbox_supervisor()` spawns a per-sandbox uvicorn on the unique port with isolated `AI_DEV_FACTORY_RUNTIME_ROOT` (`run_sandbox.py:491`)
- `destroy()` SIGTERMs the sandbox supervisor before cleanup, removes only the sandbox subtree (`sandbox_manager.py:259–275`)
- Sandbox containers receive `AI_DEV_FACTORY_SUPERVISOR_URL` pointing to their own supervisor, not the main one (`run_sandbox.py:644–649`)
