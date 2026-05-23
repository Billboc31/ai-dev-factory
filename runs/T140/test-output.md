# Test Report — T140: Isolated sandbox runtimes and supervisors

**Date**: 2026-05-23  
**Branch**: ticket/T140-t140-isolated-sandbox-runtimes-and-supervisors  
**Tester**: Claude (Sonnet 4.6)

---

## Summary

**PASS** — All acceptance criteria met. No regressions introduced.

---

## Test Execution

### Sandbox isolation tests (new — T140)

```
python -m pytest tests/test_sandbox_isolation.py -v
```

```
tests/test_sandbox_isolation.py::test_concurrent_create_unique_ports         PASSED
tests/test_sandbox_isolation.py::test_concurrent_create_unique_compose_names PASSED
tests/test_sandbox_isolation.py::test_concurrent_create_unique_ids           PASSED
tests/test_sandbox_isolation.py::test_ports_never_collide_with_main_runtime  PASSED
tests/test_sandbox_isolation.py::test_cleanup_completed_destroys_completed_sandboxes PASSED
tests/test_sandbox_isolation.py::test_cleanup_completed_respects_age_threshold       PASSED
tests/test_sandbox_isolation.py::test_cleanup_completed_ignores_non_completed_sandboxes PASSED
tests/test_sandbox_isolation.py::test_env_files_are_isolated                 PASSED
tests/test_sandbox_isolation.py::test_isolated_runtime_root                  PASSED
tests/test_sandbox_isolation.py::test_isolated_supervisor_port               PASSED
tests/test_sandbox_isolation.py::test_concurrent_sandboxes                   PASSED
tests/test_sandbox_isolation.py::test_cleanup_isolates_main_runtime          PASSED

12 passed in 0.07s
```

### Existing sandbox test suites (regression check)

```
python -m pytest tests/test_sandbox_manager.py tests/test_sandbox_routes.py tests/test_supervisor_sandbox.py -v
```

```
35 passed in 0.77s
```

### Full test suite — regression comparison

| Branch | Passed | Failed |
|--------|--------|--------|
| main   | 884    | 45     |
| T140   | 888    | 45     |

Diff of failure lists: **empty** — T140 introduces no new failures. The 45 failures are pre-existing on main and unrelated to sandbox isolation.

---

## Acceptance Criteria

### AC1 — Sandbox UI no longer displays main runtime state
**PASS**

Each sandbox supervisor is spawned with `AI_DEV_FACTORY_RUNTIME_ROOT` set to its isolated `{sandbox_dir}/runtime`. The sandbox API container receives `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}` pointing exclusively to the sandbox supervisor, not the main one at port 8090.

Evidence: `run_sandbox.py:491–535` (`_start_sandbox_supervisor`), `run_sandbox.py:644–649` (env injection).

### AC2 — Sandbox API communicates only with sandbox supervisor
**PASS**

`_write_sandbox_env()` injects:
- `AI_DEV_FACTORY_SUPERVISOR_PORT={8090 + slot}`
- `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{port}`

The sandbox API container has no access to the main supervisor URL.

Evidence: `run_sandbox.py:211–220`, `sandbox_manager.py:133`.

### AC3 — Each sandbox has its own runtime root
**PASS**

`sandbox_manager.py:138`: `sandbox_runtime_root = str(sandbox_dir / "runtime")`  
`run_sandbox.py:595–598`: creates `state/`, `logs/`, `runs/` subdirectories under the sandbox runtime root.  
`test_isolated_runtime_root`: verifies two sandboxes have distinct paths and a sentinel file in s1's root does not appear in s2's root.

### AC4 — Each sandbox has its own supervisor instance
**PASS**

`_start_sandbox_supervisor()` spawns a uvicorn process on `127.0.0.1:{supervisor_port}` with an isolated runtime root per sandbox. The PID is written to `{sandbox_runtime_root}/supervisor.pid`.  
`test_isolated_supervisor_port`: verifies each sandbox gets a unique, non-zero port ≠ 8090.

### AC5 — Multiple sandboxes can run simultaneously without collisions
**PASS**

Port allocation uses a file-locked registry (`port-registry.json`). Slots are unique per sandbox; supervisor port = `8090 + slot`.  
`test_concurrent_sandboxes`: 5 threads create sandboxes concurrently — verified distinct supervisor ports, distinct runtime roots, distinct slots, no port reusing 8090.

### AC6 — Sandbox cleanup does not affect the main runtime
**PASS**

`destroy()` flow:
1. `_terminate_sandbox_supervisor()` → reads PID from `supervisor.pid`, sends `SIGTERM`
2. Removes git worktree (`--force`)
3. Runs `docker compose down` for sandbox compose project only
4. Releases port slot from registry
5. `shutil.rmtree(sandbox_dir)` — removes only the sandbox subtree

`test_cleanup_isolates_main_runtime`: verifies SIGTERM is called with the correct PID, sandbox directory is removed, and `sandboxes_dir.parent` (main runtime root) is untouched.

### AC7 — Logs, state, and proposals remain isolated per sandbox runtime
**PASS**

Each sandbox supervisor is started with its own `AI_DEV_FACTORY_RUNTIME_ROOT` pointing to `{sandbox_dir}/runtime`. State, logs, and run artifacts written by one sandbox supervisor are in a path that is unrelated to any other sandbox or the main runtime.

---

## Regressions

None. The full test suite failure set on T140 is identical to main (45 pre-existing failures, unrelated to sandbox isolation).

---

## Anomalies

None blocking. One observation:

- `compose_utils.py` (utility for compose project name normalization) was present on main already — the Explore agent initially reported it as new to T140, but `git diff main...HEAD` confirms it pre-existed. No issue with the feature; normalization is correctly applied in `sandbox_manager.py:130`.

---

## Verdict

**TEST_COMPLETE — PASS**

All 7 acceptance criteria are met. 47 sandbox-related tests pass (12 new isolation tests + 35 existing sandbox tests). No regressions introduced.
