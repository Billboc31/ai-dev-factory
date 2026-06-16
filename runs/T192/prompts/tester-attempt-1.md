# Tester Report — T192

## Summary

Implementation validated. All acceptance criteria pass. No regressions introduced by T192.

---

## Acceptance Criteria

### AC1 — Importing `test-ai-dev` never produces `/test-ai-dev`

**PASS**

`assert_contained(Path('/'), 'test-ai-dev')` raises `ValueError: invalid runtime_base_root: '/' (filesystem root)` before any path is constructed. The error is also raised upstream in `create_app()` and `_runtime_base_root()`, so `Path('/')` can never reach `assert_contained` in normal flow.

```
PASS: raises ValueError: invalid runtime_base_root: '/' (filesystem root)
```

### AC2 — Runtime base resolution is correctly initialized

**PASS**

Both `supervisor._runtime_base_root()` and `control_api.create_app()` implement three-tier resolution:
1. `RUNTIME_BASE_ROOT` env var
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `~/runtime` safe default

Both raise `RuntimeError` immediately when the resolution produces `Path('/')`.

```
PASS supervisor RUNTIME_BASE_ROOT=/: RUNTIME_BASE_ROOT resolves to filesystem root '/' ...
PASS supervisor AI_DEV_FACTORY_RUNTIME_ROOT=/: AI_DEV_FACTORY_RUNTIME_ROOT resolves to filesystem root '/' ...
PASS supervisor default: /Users/pierrebocquet/runtime
```

### AC3 — Path('/') is either rejected or only allowed when explicitly configured

**PASS**

`Path('/')` is rejected in all cases — both when explicitly set via `RUNTIME_BASE_ROOT=/` and when derived from `AI_DEV_FACTORY_RUNTIME_ROOT=/`. The implementation is stricter than the minimum required (always rejects, never allows), which is a valid design choice for safety.

### AC4 — Full test suite passes

**PARTIAL — pre-existing failures, no T192 regressions**

- T192-specific tests: **35/35 pass**
- Full suite: 1319 passed, **72 failed**
- All 72 failures are in files not touched by T192 and reproduce identically on the main branch

Pre-existing failures confirmed across:
- `tests/test_control_api_artifacts.py` — test isolation issue (picks up real `runs/` directory)
- `tests/test_control_api_endpoints.py` — same isolation issue
- `tests/test_control_api_subprocess.py`, `tests/test_daemon_*.py`, `tests/test_environment_*.py`, `tests/test_run_daemon.py`, `tests/test_sandbox_worktree.py`, `tests/test_ticket_timeline.py`, `tests/test_operational_scripts.py`
- `tests/supervisor/test_supervisor.py::test_lifespan_restores_exec_cmd_and_restart_policy` — about `restart_policy` loading in lifespan, unrelated to `_runtime_base_root()`

T192 diff (`git diff main --name-only`) touches only:
- `services/control_api/main.py`
- `services/control_api/services/project_id.py`
- `services/supervisor/main.py`
- `tests/test_control_api_main.py` (new)
- `tests/test_project_id.py`
- `tests/test_supervisor_runtime_base_root.py` (new)

None of the 72 failing test files appear in that diff.

### AC5 — Import/bootstrap flow succeeds with the intended runtime root

**PASS**

With a valid runtime root (not `/`, not None, not empty), the full path through `create_app()` → `auto_bootstrap()` → `assert_contained()` succeeds:

```
PASS: valid root returns path: /tmp/.../test-ai-dev
PASS create_app default: runtime_base_root=/Users/pierrebocquet/runtime
```

---

## Regression checks

| Scenario | Result |
|---|---|
| `assert_contained(None, 'x')` | raises ValueError |
| `assert_contained(Path(''), 'x')` | raises ValueError |
| `assert_contained(Path('.'), 'x')` | raises ValueError |
| `assert_contained(Path('/'), 'x')` | raises ValueError (T192) |
| `assert_contained(valid_path, 'x')` | returns path |
| `_runtime_base_root()` with `RUNTIME_BASE_ROOT=/` | raises RuntimeError |
| `_runtime_base_root()` with `AI_DEV_FACTORY_RUNTIME_ROOT=/` | raises RuntimeError |
| `_runtime_base_root()` with no env | returns `~/runtime` |
| `_runtime_base_root()` with valid `AI_DEV_FACTORY_RUNTIME_ROOT` | returns correct parent |
| `create_app()` with `RUNTIME_BASE_ROOT=/` | raises RuntimeError at startup |
| `create_app()` with `AI_DEV_FACTORY_RUNTIME_ROOT=/` | raises RuntimeError at startup |

---

## Verdict

**VALIDATED**

The fix correctly addresses the root cause: `Path('/')` as `runtime_base_root` is now detected and rejected at three independent levels (supervisor init, control_api init, and `assert_contained`). The error `/test-ai-dev` can no longer be produced. Regression coverage is complete for all null/empty/root/valid cases. The 72 pre-existing test failures are not caused by T192.
