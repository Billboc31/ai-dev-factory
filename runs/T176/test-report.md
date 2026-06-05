# T176 — Test Report

## Summary

**Result: PASS** — All 7 acceptance criteria satisfied. No regressions introduced.

---

## Acceptance Criteria

### AC1 — Redeploy no longer fails when `source/.ai-dev-factory/scripts` is missing

**Status: PASS**

`_is_source_clone_valid` (sandbox_runtime_deploy.py:254) checks for `.git` and `.ai-dev-factory/scripts` before deploying. When either is missing, `_rehydrate_source_clone` is invoked automatically. The old hard-fail path on missing scripts is removed.

Verified:
- `_is_source_clone_valid` returns `False` for missing dir, missing `.git`, missing scripts dir
- `_is_source_clone_valid` returns `True` only when all three conditions are met
- `needs_rehydration` logic triggers correctly when source is missing

---

### AC2 — Missing source clone is automatically recreated

**Status: PASS**

`_rehydrate_source_clone` (sandbox_runtime_deploy.py:263) calls `_clone_fresh_source` which performs a full `git clone` into the expected source path. The old source directory is removed first if partially present.

Verified: mock-confirmed delegation from `_rehydrate_source_clone` to `_clone_fresh_source`.

---

### AC3 — Correct branch/ref is restored automatically

**Status: PASS**

`state.ref` is passed to `_clone_fresh_source` which clones `--branch <ref>` and then verifies the checked-out branch matches. Aborts with an error on branch mismatch.

Verified by existing test `test_deploy_operational_runtime_clones_fresh_source_on_ref` (passing).

---

### AC4 — Logs clearly indicate clone rehydration

**Status: PASS**

`_rehydrate_source_clone` emits all 6 required log lines before and after clone:

```
source clone missing or invalid
rehydrating sandbox source clone
repo=<project_root>
branch=<ref or (default)>
source_path=<path>
sandbox source clone restored successfully
```

Verified by direct log capture test — all lines confirmed present.

---

### AC5 — Advanced runtime options are available but collapsed by default

**Status: PASS**

`CreateEnvironmentModal.jsx`:
- `showAdvancedRuntime` state initialized to `false`
- Toggle button labeled "Advanced runtime options" with `▸/▾` indicator
- Advanced section rendered only when `{showAdvancedRuntime && (`

Verified: all UI structure checks passed.

---

### AC6 — Users can force source refresh/reclone

**Status: PASS**

Advanced section contains a `force_source_refresh` checkbox. When checked:
- Sent in the API payload (`force_source_refresh: true`)
- Stored in `SandboxState.force_source_refresh`
- `needs_rehydration` becomes `True` even when source clone is valid

Verified: `needs_rehydration=True` when `force_source_refresh=True` and source valid.

---

### AC7 — Runtime validation still prevents cross-runtime path mismatches

**Status: PASS**

`_validate_runtime_consistency` (environment_provision.py:93) is unchanged and still:
- Rejects sandbox inside project root
- Rejects project inside sandbox
- Rejects identical paths
- Rejects sandbox when parent directory doesn't exist

Verified: all 4 cases confirmed.

---

## Additional verifications

| Check | Result |
|---|---|
| `SandboxState` gains `runtime_root`, `effective_runtime_root`, `force_source_refresh` | PASS |
| `CreateEnvironmentRequest` has `runtime_root` + `force_source_refresh` | PASS |
| API rejects relative `runtime_root` with HTTP 400 | PASS |
| API rejects `runtime_root` with `..` with HTTP 400 | PASS |
| `_resolve_runtime_root` returns `source=auto` when no override | PASS |
| `_resolve_runtime_root` returns `source=override` + derived sandbox dir when set | PASS |
| `runtime_root_source=auto` logged during auto deploy | PASS |
| `runtime_root_source=override` logged during override deploy | PASS |
| `effective_runtime_root` persisted to state during deploy | PASS |
| `provision_environment` accepts and stores `runtime_root` + `force_source_refresh` | PASS |
| `provision_environment_from_body` forwards both fields | PASS |

---

## Test suite

Scope: `test_sandbox_runtime_deploy.py` + `test_environment_routes.py`

- 41/42 tests pass
- 1 failure: `test_create_environment_auto_creates_nested_custom_sandbox_path` — **pre-existing on `main` branch**, unrelated to T176

Broader regression: 65 failures in full test suite — all confirmed pre-existing on main by running identical tests against `clones/ai-dev-factory` (main). No new failures introduced.

---

## Blocking issues

None.

---

## Validation decision

**PASS** — Implementation satisfies all acceptance criteria. Redeploy is now self-healing, rehydration logs are correct, force-refresh works, runtime root override is end-to-end wired, and the UI exposes advanced controls collapsed by default.
