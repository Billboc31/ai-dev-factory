I have all the information I need. Let me compile the review.

---

## Review — T157: Ensure deployer fetches and checks out the requested branch before deployment

### Summary

The implementation directly addresses all ticket requirements. Four files were modified: `SandboxState` model, `sandbox_manager.py`, `deployer.py`, and `test_sandbox_worktree.py`. The changes are tightly scoped and backward-compatible.

---

### Correctness against acceptance criteria

| Criterion | Status | Notes |
|---|---|---|
| Fetch latest remote commit before sandbox creation | ✅ | `git fetch origin <branch>` runs before `git worktree add` |
| Sandbox worktree HEAD equals fetched remote branch HEAD | ✅ | `git rev-parse origin/<branch>` → SHA used in `--detach <sha>` |
| New commit pushed → subsequent deploy uses it | ✅ | Every deploy fetches fresh; SHA resolved after fetch |
| Missing branch fails with clear error, no silent fallback to main | ✅ | `RuntimeError` raised with branch name, sandbox destroyed |
| SandboxState exposes deployed ref and commit SHA | ✅ | `requested_ref`, `resolved_ref`, `commit_sha` persisted to `state.json` |
| Runtime UI can display deployed commit/ref | ✅ | Fields in model, serialized via `model_dump_json` |
| Existing deploys from main still work | ✅ | No-branch path routes to existing `run_deploy` unchanged |
| Sandbox isolation intact | ✅ | Worktree per sandbox, no mutation of main clone working tree |

---

### Code quality

**`sandbox_manager.py:239–310`** — Logic is clean and correct:
- Fetch → rev-parse → worktree add, in that order, each step gated on the previous
- Both fetch failure and rev-parse failure paths destroy the sandbox before raising
- `--detach <sha>` eliminates any ambiguity about which commit is checked out
- State identity fields correctly initialized to `None` for the no-branch path

**`_do_deploy` in `deployer_runner.py:260`** — Correctly uses `Path(sandbox.worktree_path)` as `cwd` when a sandbox is provided. Deploy scripts execute against the fetched branch code. ✅

**`deployer.py:50–70`** — Route change is minimal. Lazy `SandboxManager` init via app state is a workable pattern. Backward compat is preserved cleanly.

---

### Tests

4 new tests cover the critical behaviors:

- `test_create_with_worktree_fetches_before_checkout` — ordering assertion ✅
- `test_create_with_worktree_uses_remote_sha_not_branch_name` — SHA vs branch name ✅
- `test_create_with_worktree_fails_loudly_if_fetch_fails` — loud failure + sandbox destroyed ✅
- `test_create_with_worktree_records_ref_identity_in_state` — all 3 fields persist to disk ✅

---

### Minor observations (non-blocking)

1. **`rev-parse` failure path has no test.** If `git fetch origin <branch>` succeeds but `git rev-parse origin/<branch>` subsequently fails, the sandbox is destroyed and a `RuntimeError` is raised correctly — but there is no dedicated test for this path. Low risk given how unlikely this is after a successful fetch, but the coverage gap exists.

2. **`sandbox_manager: object` type hint in `deployer_runner.py:371`.** This is imprecise. `SandboxManager` is the concrete type; using `object` loses IDE and static analysis benefits. Not a functional issue.

3. **No route-level integration test for `POST /projects/{id}/deployer/deploy` with a branch body.** The unit tests thoroughly cover `create_with_worktree`, but the thin `trigger_deploy` route is untested. Not blocking given simplicity of the route.

---

### Scope compliance

Changes are bounded to: deployer route, sandbox manager worktree logic, sandbox model, and tests. No changes to Traefik, ports, smoke tests, persistent environment management, or merge/rebase logic. Fully compliant with ticket exclusions and constraints.

---

### Verdict

The implementation is correct, well-scoped, and satisfies all acceptance criteria. The observations above are non-blocking.

IMPLEMENTATION_APPROVED
