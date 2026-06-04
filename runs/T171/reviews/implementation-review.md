Good — I can now see that `_register_proxy_routes_after_compose()` is called as a callback inside `_on_step_complete` (after `start.sh` runs), which is well after the clone step. So when a clone fails, no proxy routes have been registered yet. The missing `urls`/`route_registered=True` in the new failure path is intentional and correct — not a regression.

Now I have enough information to write the complete review.

---

## Review — T171: Environment deploy should use a fresh runtime checkout

### Summary

The implementation replaces the previous `git worktree add` approach with a `git clone --branch <ref>` pattern, creating a fresh `source/` directory per sandbox. All mandatory acceptance criteria from the ticket are addressed. Code quality is good, test coverage is purposeful. One minor semantic issue is noted.

---

### Correctness vs. Ticket Requirements

**Fresh runtime checkout** — `create_with_source()` (`sandbox_manager.py:407-462`) clones `project_root` into `sandbox_dir / "source"` via `git clone --branch <ref>`. The worktree approach is fully removed from the provisioning path.

**Branch verification** — Implemented at two levels:
- Provisioning: `sandbox_manager.py:431-441` — runs `git branch --show-current` post-clone, raises `RuntimeError` with "branch mismatch" on mismatch.
- Runtime deploy: `sandbox_runtime_deploy.py:226-245` — same check inside `_clone_fresh_source()`, returns `(False, err, sha)` on mismatch.

**Required log output** — `_clone_fresh_source()` (`sandbox_runtime_deploy.py:238-240`) logs all three required lines:
```
pwd: <source_path>
git branch --show-current: <branch>
git rev-parse --short HEAD: <sha>
```

**Abort on clone failure** — Clone failure in `deploy_operational_runtime` stops the supervisor and returns `OperationalDeployResult(success=False, ...)` before any scripts run. This is verified by the test `test_deploy_operational_runtime_aborts_on_clone_failure` which asserts `not scripts_called`.

**Isolation across environments** — Each sandbox uses `self._sandbox_dir(state.id) / "source"`, so concurrent deploys of different branches never share a source directory.

**Backward compatibility** — Both `sandbox_manager.py:597-610` and `routes/sandbox.py:387-417` maintain legacy `worktree_path` cleanup paths for existing state files.

---

### Code Quality

**`_clone_fresh_source` function** — Clean, well-scoped helper. Returns a typed tuple `(bool, str | None, str | None)`. Logging is structured and matches the ticket spec exactly. Removing the existing source with `shutil.rmtree` before cloning ensures determinism on re-deploy.

**`deploy_operational_runtime` signature** — The removal of `use_worktree: bool = False` is correct. The proxy route registration happens inside `_on_step_complete` (called from `_run_scripts` after `start.sh`), which is after the clone step, so the clone failure path correctly omits `urls`/`route_registered` — there are no routes to clean up at that point.

**`deployer_runner.py` `cwd` resolution** — The fallback chain `source_path → worktree_path → project_root` is a correct and safe ordering.

---

### Minor Observations (non-blocking)

**`resolved_ref` is now equal to `requested_ref`** (`sandbox_manager.py:453`): The original code stored `origin/<branch>` in `resolved_ref` (the actual remote ref after `fetch`+`rev-parse`). The new code sets `resolved_ref = requested_ref`, so both fields hold the same branch name string. The actual commit SHA is stored separately in `commit_sha`, so no information is lost, but the field's name is now slightly misleading. Not blocking, but a future cleanup could remove the field or rename it.

**No branch verification when `branch=None`** in `create_with_source`: When called without a branch, the method clones the default branch with no verification. This is consistent with the ticket scope (which focuses on named branch deployments), but callers should be aware that `branch=None` paths are unverified.

**Test: `test_create_with_source_uses_clone`** (`test_sandbox_manager.py:620`) — The mock returns `"abc1234\n"` for all non-branch commands. This means `git rev-parse --short HEAD` returns `"abc1234"` with the trailing newline stripped by `.strip()`, so `commit_sha = "abc1234"`. The assertion `assert state.commit_sha == "abc1234"` is correct. No issue.

---

### Scope Compliance

No scope creep detected. The implementation changes exactly the provisioning and runtime deploy paths required by the ticket. Auth, routing, state persistence, and other subsystems are touched only to swap `worktree_path` → `source_path` where necessary.

---

### Test Coverage

| Test | Covers |
|---|---|
| `test_create_with_source_uses_clone` | clone called, worktree not called, state fields set |
| `test_create_with_source_aborts_on_clone_failure` | RuntimeError + sandbox destroyed |
| `test_create_with_source_aborts_on_branch_mismatch` | RuntimeError on wrong branch |
| `test_source_removed_after_undeploy` | `shutil.rmtree` on source path |
| `test_legacy_worktree_removed_after_undeploy` | backward compat cleanup |
| `test_deploy_operational_runtime_clones_fresh_source_on_ref` | end-to-end with clone + success |
| `test_deploy_operational_runtime_aborts_on_clone_failure` | scripts never run when clone fails |

Coverage is complete for the happy path and all critical failure modes. The backward-compat paths are tested.

---

### Conclusion

The implementation correctly and completely addresses the ticket. Fresh clone, branch verification, required logging, isolation, and failure handling are all in place. The one semantic observation about `resolved_ref` is a minor code clarity issue, not a correctness issue.

IMPLEMENTATION_APPROVED
