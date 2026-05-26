All 133 sandbox-related tests pass. The 47 failures are pre-existing and unrelated to T147 (they affect control API endpoints, daemon checkpoint, and run daemon modules unchanged by this ticket).

---

## Test Report — T147 Sandbox Daemon Isolation

### Acceptance Criteria

| Criterion | Status |
|---|---|
| Sandbox daemon no longer requires manual host commands | **PASS** — `_start_sandbox_supervisor()` spawns the uvicorn subprocess programmatically via the API (`start()` / `stop()` / `destroy()`) |
| Each sandbox has its own daemon instance | **PASS** — `test_isolated_daemon_startup` confirms a separate `Popen` call per sandbox, PID stored in state; `test_concurrent_sandbox_daemons` confirms two simultaneous sandboxes get distinct PIDs |
| Sandbox daemon uses sandbox runtime root only | **PASS** — `test_sandbox_runtime_root_isolation` verifies `.env` sets `AI_DEV_FACTORY_RUNTIME_ROOT` to the per-sandbox path; supervisor subprocess is launched with the same isolated env var |
| Multiple sandbox daemons can run simultaneously | **PASS** — `test_concurrent_sandbox_daemons` confirms distinct ports (8091, 8092, …), distinct runtime roots, and distinct PIDs for each concurrent sandbox |
| Sandbox cleanup does not affect the main daemon | **PASS** — `test_isolated_daemon_shutdown` and `test_cleanup_safety` both place a `main_runtime/daemon.pid` file outside the sandbox tree, confirm it is untouched after `stop()` / `destroy()` |
| Implementation remains generic and project-agnostic | **PASS** — no project-specific paths or names hardcoded; runtime root and supervisor port are derived from slot index and sandbox ID |

### Test Results

```
5/5 passed  tests/test_sandbox_daemon_isolation.py
133/133 passed  all sandbox-related tests (daemon isolation + manager + routes + isolation + worktree + supervisor)
```

### Regressions

None. The 47 failures in `test_control_api_endpoints`, `test_control_api_subprocess`, `test_daemon_checkpoint`, `test_daemon_issue_polling`, `test_run_daemon`, and `test_ticket_timeline` are pre-existing and reproduce identically on the `main` branch — they are not caused by T147 changes.

### Conclusion

**VALIDATION PASS.** All five acceptance criteria are met. The implementation is complete and correct.
