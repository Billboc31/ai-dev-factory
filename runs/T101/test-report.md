# Test Report — T101

**Date**: 2026-05-15
**Branch**: ticket/T101-t101-runtime-hardening-checkpoint-timeline-mapping
**State at test time**: IMPLEMENTATION_APPROVED

---

## Summary

6 of 7 acceptance criteria pass. 1 fails (blocking).

| Criterion | Status |
|---|---|
| `IMPLEMENTATION_REVIEW_NEEDED` not displayed as human pause | PASS |
| Next ticket after T034 is T035 (numeric id allocation) | PASS |
| Code files in COMMIT_SCOPE are auto-checkpointed | PASS |
| Unknown files continue to block the daemon | PASS |
| TEST_COMPLETE triggers checkpoint/push before PR | PASS |
| PR created/updated only after stable push | PASS |
| Runtime files no longer pollute Git | **FAIL** |

---

## Criterion 1 — IMPLEMENTATION_REVIEW_NEEDED not displayed as human pause

**Status: PASS**

`services/control_api/services/artifact_reader.py:151-152`:

```python
"IMPLEMENTATION_REVIEW_NEEDED": (
    ["done", "done", "done", "done", "running", "pending", "pending"], False),
```

`human_gate=False` — reviewer step displays as "running" (auto-runnable), not "waiting_human".

Full expected mapping confirmed:

| State | human_gate | reviewer step |
|---|---|---|
| PLAN_REVIEW_NEEDED | True | — |
| IMPLEMENTATION_REVIEW_NEEDED | False | running |
| IMPLEMENTATION_FIX_REQUIRED | False | running |
| IMPLEMENTATION_APPROVED | False | running |
| TEST_COMPLETE | True | — |

Test: `test_ticket_timeline.py::test_timeline_implementation_review_needed` — PASSED

---

## Criterion 2 — Numeric ticket id allocation

**Status: PASS**

`tools/agent_runner/run_daemon.py:690-701`:

```python
def next_ticket_id(runs_dir: Path, reserved: set[str] | None = None) -> str:
    max_num = 0
    for p in runs_dir.glob("T*/"):
        m = re.match(r"T(\d+)$", p.name)
        if m:
            max_num = max(max_num, int(m.group(1)))
    ...
    return f"T{max_num + 1:03d}"
```

Numeric parsing via `re.match(r"T(\d+)$")` + `int()` + zero-padded format string.

Tests passing:
- `test_next_ticket_id_t034_gives_t035` — T034 → T035
- `test_next_ticket_id_t099_gives_t100` — T099 → T100
- `test_next_ticket_id_lexicographic_trap` — T001, T010, T100 → T101 (not T11)
- `test_next_ticket_id_with_gaps` — non-contiguous ids handled correctly

---

## Criterion 3 — Code files in COMMIT_SCOPE auto-checkpointed

**Status: PASS**

`tools/agent_runner/run_daemon.py:252-331`:

`_classify_dirty_files()` returns a 3-tuple `(workflow_artifacts, code_scope_files, unknown_files)`.
`_CODE_SCOPE_PREFIXES` mirrors `run_ticket.py`'s COMMIT_SCOPE: `tools/`, `tests/`, `services/`, `apps/`, etc.

`_ensure_clean_working_tree()` auto-triggers `run_ticket.py --commit --include-code` when code-scope files are dirty, without blocking daemon progress.

Tests passing:
- `test_classify_dirty_files_code_scope_files_are_not_unknown`
- `test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint`
- `test_ensure_clean_working_tree_code_scope_files_do_not_block_when_no_unknown`

---

## Criterion 4 — Unknown files continue to block the daemon

**Status: PASS**

`tools/agent_runner/run_daemon.py:296-299`:

```python
if unknown_files:
    _log(f"{ticket_id}: pre-flight abort — unknown dirty files: {unknown_files!r}")
    _log(f"{ticket_id}: pre-flight abort — commit or stash unknown files before daemon can proceed")
    return False
```

Files outside `runs/` and outside `_CODE_SCOPE_PREFIXES` still trigger safe abort.

Tests passing:
- `test_classify_dirty_files_non_scope_files_are_unknown`
- `test_ensure_clean_working_tree_unknown_files_aborts`
- `test_launch_ticket_aborts_when_unknown_dirty_files`

---

## Criterion 5 — TEST_COMPLETE triggers checkpoint/push before PR

**Status: PASS**

`tools/agent_runner/run_daemon.py:539-577`:

`_checkpoint_and_push_before_pr()` calls `run_ticket.py --commit --include-code` then `run_ticket.py --push` before returning.

`handle_test_complete()` at line 570-577 gates all PR creation on this function returning `True`.

Tests passing:
- `test_checkpoint_and_push_before_pr_calls_commit_with_include_code`
- `test_checkpoint_and_push_before_pr_pushes_after_successful_commit`
- `test_checkpoint_and_push_before_pr_skips_push_when_nothing_to_commit`
- `test_handle_test_complete_checkpoints_before_pr`

---

## Criterion 6 — PR created only after stable push

**Status: PASS**

`handle_test_complete()` (line 573-575):

```python
if not _checkpoint_and_push_before_pr(ticket_id):
    _log(f"{ticket_id}: pre-PR push failed — PR skipped")
    return
```

If checkpoint or push fails, `create_or_update_pr()` is never called.

Tests passing:
- `test_handle_test_complete_skips_pr_when_push_fails`
- `test_handle_test_complete_orchestrates_pr_and_issue`

---

## Criterion 7 — Runtime files no longer pollute Git

**Status: FAIL — blocking**

### Finding

The `.gitignore` patterns are correctly defined (lines 10-15):

```
apps/dashboard/node_modules/
runs/daemon.pid
runs/daemon.log
runs/*/workflow-status.md
runs/*/daemon.lock
```

However, previously-tracked files were **not removed from the git index** with `git rm --cached`. The ticket task explicitly required:

> S'ils sont déjà trackés, les retirer du tracking avec `git rm --cached`, sans supprimer les fichiers locaux utiles.

Current state of tracked files that should be untracked:

```
apps/dashboard/node_modules/   → 6,878 tracked files
runs/T*/workflow-status.md     → 24 tracked files (T003 through existing tickets)
apps/dashboard/.vite/          → tracked (vitest results)
```

Because these files remain in the git index, they will continue to appear in `git status`, dirty tree checks, and commits — exactly the pollution T101 aimed to eliminate.

### Required fix

```bash
git rm -r --cached apps/dashboard/node_modules/
git rm --cached runs/T*/workflow-status.md
git rm -r --cached apps/dashboard/.vite/
```

Then commit the removals.

---

## No `git add .`

Verified: no `git add .` call in `run_daemon.py`, `run_ticket.py`, or any test file. The only occurrences are in comments and test assertions that guard against it.

---

## Test suite results

All 102 unit tests pass:

```
tests/test_ticket_timeline.py        9 passed
tests/test_daemon_issue_polling.py  47 passed
tests/test_daemon_checkpoint.py     22 passed
tests/test_daemon_pr_lifecycle.py   24 passed
```

---

## Verdict

**FAIL — blocking issue found.**

Criterion 7 (runtime files no longer pollute Git) is not met. The `.gitignore` additions are correct, but `git rm --cached` was never run to remove the 6,900+ already-tracked node_modules and workflow-status files from the index.

The implementation is otherwise complete and correct. Once the `git rm --cached` step is executed and committed, all acceptance criteria will be satisfied.
