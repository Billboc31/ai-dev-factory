I have now read all the relevant artifacts. Here is my structured review.

---

## Review — T017 — Workflow-aware commit and push

### Summary

The implementation adds `--include-code` staging, `_warn_out_of_scope`, branch guardrails on commit and push, a dirty-tree warning on push, and 12 unit tests. Two files were touched: `tools/agent_runner/run_ticket.py` and `tests/test_commit_push.py`.

---

### Checks

#### 1. Staging scope is explicit

`COMMIT_SCOPE` is a frozen tuple at module level (line 75–82). Each path is added individually in a loop (`git add {path}` — one arg per call). The `--include-code` flag is the only way to extend staging beyond `runs/TXXX/`. No implicit widening.

**PASS**

#### 2. No unsafe global staging

`git add .` and `git add -A` are absent from the entire file. `test_commit_never_calls_git_add_dot` further enforces `len(args) == 3` on every `git add` call, preventing multi-path expansions as well.

**PASS**

#### 3. Branch validation

`commit_ticket()` reads `expected_branch` from `state.json` before touching the tree; refuses with `rc=2` on mismatch (lines 204–215). `push_branch()` applies the same guard (lines 273–284). Both log the refusal to `runtime.log`. Tests `test_commit_refused_on_wrong_branch` and `test_push_refused_on_wrong_branch` cover both paths.

**PASS**

#### 4. Push targets correct ticket branch

`push_branch()` derives `push_target` from `state.json["branch"]` when present; falls back to `branch_name(ticket_id, slug)` only when `state.json` is absent (with a warning). The push command is `git push -u origin {push_target}` — explicit, never computed ad hoc. `test_push_only_pushes_ticket_branch` verifies the branch name in the actual push call.

**PASS**

#### 5. Runtime Git logs

`_log_runtime()` is called at every Git decision point: branch mismatch, dirty tree, nothing to commit, staging failure, commit sha, push start/success/failure, and auto-commit/auto-push events. Log path: `runs/TXXX/runtime.log`.

**PASS**

#### 6. Workflow compatibility preserved

`auto_run` calls `commit_ticket(ticket_id, None)` with no `include_code` argument — defaults to `False`, meaning `--auto-commit` behavior is unchanged. `--auto-init`, `--ensure-branch`, fix loops, and review loops are untouched. Implementation output reports 43/43 tests passing.

**PASS**

#### 7. Changes remain bounded

Only two files changed (`run_ticket.py`, `tests/test_commit_push.py`). The modifications in `run_ticket.py` are the five declared in the plan. No new dependencies, no scope creep.

**PASS**

---

### Minor observations (non-blocking)

- `_warn_out_of_scope` is only invoked when `include_code=True`. In the `include_code=False` path, the user sees the message "only runs/ artifacts are auto-staged — stage other changes manually", which is sufficient.
- The "nothing to commit" check uses scoped paths (`git status --porcelain {stage_paths}`) rather than a global check, which is correct and intentional.
- `push_branch` warns on dirty working tree but does not block — this matches the plan's stated design ("non-blocking warning"). Acceptable given push is separate from staging.

---

### Verdict

All acceptance criteria from the ticket are satisfied. The plan is implemented faithfully, the tests are meaningful and cover the edge cases, and no regressions were introduced.

IMPLEMENTATION_APPROVED
