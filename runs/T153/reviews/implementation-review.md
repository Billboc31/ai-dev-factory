I have all the context needed to write a complete review.

---

# Implementation Review — T153: Generic Smoke Tests and Fix Proposal

## Scope verification

The plan was simplified from the original ticket after a mandatory `PLAN_FIX_REQUIRED` review. The approved scope covers:

1. Generic smoke-test lifecycle after healthcheck (`_run_smoke_tests`)
2. Distinct `healthcheck_status` / `smoke_status` schema fields
3. `validation.json` artifact written on every run
4. AI fix-proposal generation via `exec_cmd` (read-only, no patch application)
5. New test coverage

The full bounded auto-fix loop (apply patch → redeploy → retry) was explicitly deferred by the plan reviewer to a follow-up ticket. This is consistent with the plan.md and reflected correctly in the implementation.

---

## Correctness vs approved plan acceptance criteria

| Criterion | Status |
|---|---|
| `smoke.sh` executed after healthcheck when present; skipped otherwise | ✅ `run_sandbox._run_smoke_tests` lines 628–673 |
| Smoke test receives `SANDBOX_WEB_URL` / `SANDBOX_API_URL` | ✅ `extra_env` passed through; test `test_smoke_receives_proxy_urls` |
| `SandboxValidationState` exposes distinct `healthcheck_status` and `smoke_status` | ✅ `schemas.py:305-306` |
| `validation.json` written to `${SANDBOX_RUNTIME_ROOT}/validation.json` always | ✅ `_write_validation_json` called unconditionally |
| `fix-proposal.md` written when `AI_DEV_FACTORY_EXEC_CMD` set and smoke fails | ✅ `_call_fix_proposer` |
| No hardcoded AI SDK | ✅ only `subprocess.run(exec_cmd, shell=True, ...)` |
| Cleanup/undeploy still executes after validation | ✅ `finally:` block in `_do_sandbox` |
| `"skipped"` accepted in schema | ✅ `SandboxValidationStep.status` now includes `"skipped"` |
| New tests pass | ✅ 13 new test cases (10 + 3) |

---

## Strengths

- **Consistent dual coverage**: both `run_sandbox.py` (the sandbox pipeline) and `deployer_runner.py` (the legacy deploy pipeline) received the smoke-test integration. The separation is clean.
- **`validation.json` always written**: observable artifact regardless of outcome — good for debugging and future iteration-history work.
- **Fix proposer is read-only by design**: writes only to `sandbox_runtime_root`, never modifies worktree or project files. Correct safety boundary.
- **Test quality**: the 10 new smoke-test cases in `test_run_sandbox_worker.py` cover all meaningful branches — absent/pass/fail smoke, proxy URL injection, validation.json content on success and failure, fix-proposal with/without exec_cmd, smoke skipped on prior required-script failure, healthcheck_status on HC failure.
- **No provider lock-in**: `AI_DEV_FACTORY_EXEC_CMD` is a plain shell command string. Clean abstraction.

---

## Minor observations (non-blocking)

**1. `_call_fix_proposer` doesn't log or guard on `exec_cmd` exit code** (`run_sandbox.py:754-776`)

```python
result = subprocess.run(exec_cmd, shell=True, ...)
if result.stderr:
    _append_log(log_path, f"fix proposer stderr: {result.stderr[:500]}\n")
proposal_path = sandbox_runtime_root / "fix-proposal.md"
proposal_path.write_text(result.stdout, encoding="utf-8")  # written regardless of rc
```

If `exec_cmd` exits non-zero (e.g., Claude rate-limited or errors), `fix-proposal.md` is written with empty or partial content without any indication of failure in the log. The exit code is never checked or recorded. This will silently produce a misleading empty fix-proposal. A one-line log of `result.returncode` and a guard to skip writing when `rc != 0` would make this more transparent. Not a blocker since the file is human-reviewed anyway.

**2. `deployer_runner._run_smoke_tests` missing `stdin=DEVNULL` / `start_new_session=True`** (`deployer_runner.py:185-191`)

`run_sandbox.py` applies these flags consistently for all subprocess invocations — they allow safe `SIGKILL` on timeout via `killpg`. The deployer_runner version doesn't have them. A smoke.sh that waits for stdin or spawns subprocesses will be uncleanable on timeout. This inconsistency is a low-probability reliability risk in the non-sandbox deploy path.

**3. Smoke tests are not run in `environment` mode** (`run_sandbox.py:1008`)

```python
if success and mode == "validation":
    smoke_status, smoke_fail = _run_smoke_tests(...)
```

This is a reasonable design choice (environment mode is meant to stay running, not validate), but it's not documented anywhere — not in the code, the plan, or `deployer-fixer.md`. A future contributor may be confused that an `environment`-mode run never produces a smoke result. A brief comment would prevent this.

**4. No test for `exec_cmd` non-zero exit in `_call_fix_proposer`**

The existing test `test_fix_proposal_written_when_exec_cmd_set_and_smoke_fails` uses `echo '...'` which always exits 0. There's no test asserting behavior when `exec_cmd` fails. Low risk since the function is best-effort, but the gap matches observation #1.

---

## Scope compliance

- No application source files modified. ✅
- No patch is applied automatically. ✅
- No hardcoded provider SDK introduced. ✅
- Changes bounded to: `run_sandbox.py`, `deployer_runner.py`, `deployer.py`, `schemas.py`, `ai/roles/deployer-fixer.md`, two test files. ✅
- Full bounded auto-fix loop correctly deferred to a follow-up ticket. ✅

---

## Verdict

Implementation is correct, well-tested, and compliant with the approved plan scope. The minor observations above are quality improvements for a follow-up — none of them affect the correctness of the delivered functionality.

IMPLEMENTATION_APPROVED
