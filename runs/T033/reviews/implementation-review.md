I have a complete picture. Now I'll write the formal review.

---

# Review — T033 — Automatic workflow checkpoint commits

## Scope check

The implementation touches exactly the files declared in the plan:
- `run_issue_intake.py` — bootstrap checkpoint
- `run_daemon.py` — pre-flight guard, post-intake commit, flag propagation
- `.gitignore` — deduplication (no functional change; all 4 entries already present)
- New: `tests/test_intake_checkpoint.py`, extensions to `tests/test_daemon_checkpoint.py` and `tests/test_daemon_issue_polling.py`
- `run_ticket.py` — untouched ✅

No scope drift detected.

---

## Requirement coverage

### 1. Bootstrap checkpoint after intake

`commit_bootstrap(ticket_id, push=False)` in `run_issue_intake.py`:
- Stages only `runs/TXXX/ticket.md` — never `git add .` ✅
- Non-blocking: catches all errors, logs to `runtime.log`, never raises ✅
- Propagated from `run_intake()` via `push=` flag, exposed on CLI as `--push` ✅
- Logs: `"bootstrap checkpoint completed for T033"`, `"checkpoint push for T033"` ✅

`state.json` is correctly excluded: it is gitignored (`runs/*/state.json`) so it cannot be staged. Only `ticket.md` is the right artifact here.

### 2. Post-intake commit of `.issue-intake.json`

`_commit_after_intake(ticket_id)` in `run_daemon.py` calls `run_ticket.py TXXX --commit --include-code`.

Key detail: `COMMIT_SCOPE` in `run_ticket.py` (line 84) includes `"runs/"` — the entire `runs/` subtree. Therefore `git add runs/` in `commit_ticket()` DOES stage `runs/.issue-intake.json`. The docstring "to include .issue-intake.json" is correct, even though it goes through the `runs/` COMMIT_SCOPE entry rather than a direct stage. ✅

Sequence in `poll_github_issues()`:
1. `call_issue_intake(push=True)` → writes `ticket.md`, commits it, pushes
2. `save_issue_index()` → writes `runs/.issue-intake.json`
3. `_commit_after_intake()` → stages `runs/T033/` + `runs/` (via COMMIT_SCOPE) → commits `.issue-intake.json`

Two-commit pattern is intentional and correct. ✅

### 3. Pre-flight dirty tree guard

`_classify_dirty_files()` parsing is correct:
- `line[3:]` for standard porcelain format
- `" -> "` split for rename operations — test coverage confirmed ✅
- Returns `([], [])` on git failure (safe default) ✅

`_ensure_clean_working_tree(ticket_id, auto_push)`:
- Clean tree → `True` ✅
- Unknown files dirty → log + `False` (safe abort) ✅
- Only workflow artifacts dirty → `run_ticket.py TXXX --commit --include-code` → COMMIT_SCOPE includes `runs/`, so ALL dirty `runs/` files are committed, not just `runs/TXXX/` ✅
- commit `rc=1` (nothing to commit) → proceeds (`True`) ✅
- commit `rc>1` → abort (`False`) ✅

**Lock safety**: lock is acquired BEFORE `_ensure_clean_working_tree()` and released in `finally`. Pre-flight cannot race with a concurrent daemon instance. ✅

The cross-ticket dirty artifact scenario (T001 generates artifacts, T002 runs pre-flight) IS handled correctly because `git add runs/` (from `--include-code`) stages all dirty `runs/` files regardless of ticket prefix.

### 4. Gate 5 coverage

`run_ticket.py --auto` has `_check_working_tree_clean()` at line 755 before any step executes. The pre-flight guard in `launch_ticket()` ensures this gate is never hit for workflow-artifact-driven dirty state. ✅

### 5. gitignore

All four required runtime patterns were already present at lines 8–11. Lines 14–17 were exact duplicates and have been removed. No functional change, no regressions. ✅

### 6. Logs

Observable log lines confirmed in implementation:
- `"checkpoint commit for T033"` — pre-flight and post-intake paths
- `"checkpoint push for T033"` — push path
- `"bootstrap checkpoint completed for {ticket_id}"` — intake bootstrap
- `"{ticket_id}: pre-flight abort — unknown dirty files: ..."` — safe abort
- `"{ticket_id}: nothing new to commit after intake"` — rc=1 path ✅

### 7. Constraints

- Never uses `git add .` ✅
- `run_ticket.py` unmodified — canonical commit system reused ✅
- `COMMIT_SCOPE` respected ✅
- Human gate states (`PLAN_REVIEW_NEEDED`, `TEST_COMPLETE`) untouched ✅
- No direct `state.json` mutations introduced ✅

---

## Test suite

- 30 new tests: all pass
- Full suite: 334 passed, 1 pre-existing failure (`test_commit_with_include_code_stages_all_scope_paths` in T031-era code, unrelated to T033)
- Coverage: bootstrap staging, no-`git add .` invariant, commit message format, push flag propagation, error non-blocking, dirty-file classification, rename handling, pre-flight all three branches, lock integration, flag propagation through daemon CLI

---

## Minor observations (non-blocking)

**O1**: `poll_github_issues()` has no pre-flight call before `call_issue_intake()`. The intake's own `check_working_tree_clean()` will fail on a dirty tree and the daemon retries on the next cycle. This is pre-existing behavior and acceptable — intake with dirty tree would be incorrect. No fix required.

**O2**: With `--auto-commit` disabled and a ticket execution that leaves artifacts for a DIFFERENT ticket, the pre-flight would attempt to commit all `runs/` content (via COMMIT_SCOPE), which is actually the correct behaviour. This scenario is covered by design.

**O3**: Pre-existing test failure in `test_commit_push.py::test_commit_with_include_code_stages_all_scope_paths` originates from T031 and reflects the correct runtime behaviour (scope paths that don't exist in the test environment are silently skipped). Not a T033 regression.

---

## Acceptance criteria

| Criterion | Status |
|---|---|
| Ticket intake runs entirely without manual git intervention | ✅ |
| Workflow steps leave no dirty repo between daemon cycles | ✅ |
| Runtime transient files don't pollute git | ✅ (gitignore) |
| Daemon chains multiple cycles without working-tree blocker | ✅ |
| Canonical scripts used for commits/push | ✅ |
| No `git add .` | ✅ |
| Checkpoints observable in logs | ✅ |

---

The implementation is minimal, bounded, correct, and well-tested. All acceptance criteria met.

IMPLEMENTATION_APPROVED
