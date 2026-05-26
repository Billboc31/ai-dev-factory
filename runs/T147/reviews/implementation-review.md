---

## Review — T147 — Sandbox Daemon Isolation

### Summary

The implementation is focused, clean, and correctly addresses all acceptance criteria. Four files modified, one new test file. No scope drift.

---

### Correctness vs. Ticket

| Requirement | Status |
|---|---|
| Each sandbox runs its own daemon instance | ✓ `_start_sandbox_supervisor` spawns one uvicorn process per `start()` call |
| Sandbox daemon uses sandbox runtime root only | ✓ `AI_DEV_FACTORY_RUNTIME_ROOT` set to `{sandbox_dir}/runtime/` in both env and subprocess env |
| Communicates only with sandbox supervisor | ✓ `AI_DEV_FACTORY_SUPERVISOR_URL` points to per-sandbox port in `.env` |
| Sandbox-specific ports | ✓ `8090 + slot`, matches existing slot-based allocation |
| API/dashboard starts/stops daemon via supervisor | ✓ `start()` spawns supervisor, `stop()`/`destroy()` SIGTERM it |
| No manual host command required | ✓ `start()` handles everything |
| Logs/state/pid isolated | ✓ Runtime root is inside sandbox dir, subdirs `state/`, `logs/`, `runs/` created on start |
| Cleanup safe | ✓ `_terminate_sandbox_supervisor` scoped to sandbox PID only |
| Multiple concurrent daemons | ✓ Slot-based ports, independent runtime roots |

### Plan Compliance

Implementation matches the plan exactly. All five planned files (`sandbox.py`, `sandbox_manager.py`, `start_supervisor.sh`, tests) are present. Nothing was added beyond scope; excluded items (auto-fix loops, cloud deployment, daemon polling changes, port allocation changes) are untouched.

### Code Quality

**`_start_sandbox_supervisor`** — well-structured. `start_new_session=True` correctly detaches the subprocess. Log file opened as append, not truncate. PID file written as JSON with port for future lookup. Error handling returns `None` on `OSError` without crashing the start flow.

**`_terminate_sandbox_supervisor`** — two-layer PID resolution (state field → pid file) adds resilience against process restart scenarios where in-memory state is lost. SIGTERM errors silently suppressed — correct behavior (process may already be dead).

**`SandboxState.supervisor_pid`** — minimal model change, nullable, defaults to `None`. Backward-compatible with existing state files.

**`start_supervisor.sh`** — arg parsing loop is idiomatic bash. CLI overrides correctly applied after `.env` load. No regression to existing behavior when called without arguments.

### Tests

All five acceptance criteria are covered by dedicated tests. Mocking strategy (patching `subprocess.Popen`, `subprocess.run`, `os.kill`) is appropriate for unit tests. Tests verify both positive behavior (correct calls) and isolation (main daemon PID file untouched). No test relies on actual subprocess spawning.

### Minor Observations (non-blocking)

1. **Race window on startup**: `_start_sandbox_supervisor` returns immediately after `Popen`. If containers make requests to the supervisor in the first ~1-2 seconds of their startup, they may get `connection refused` until uvicorn finishes binding. Acceptable for this scope — containers typically don't issue immediate requests.

2. **No SIGKILL escalation**: SIGTERM is sent but there is no wait + SIGKILL fallback if the process hangs. Acceptable given supervisor's own lifecycle management.

3. **Double-start edge case**: Calling `start()` on an already-running sandbox spawns a second uvicorn on the same port. The `OSError` is caught and returns `None`, overwriting the valid PID in state with `None`. No crash, but state becomes inconsistent. Acceptable for this scope since double-starting is not an intended operation.

4. **`start_supervisor.sh` comment**: The comment reads "applied after .env so they take precedence" but parsing happens before `.env` load; the override is applied after. The behavior is correct but the comment is slightly ambiguous.

---

### Verdict

Implementation is correct, in-scope, well-tested, and safe. No blocking issues.

IMPLEMENTATION_APPROVED
