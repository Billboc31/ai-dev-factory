---

## Test Report — T103

**Verdict: FAIL — 1 blocking issue**

### Acceptance Criteria Results

| AC | Description | Status |
|---|---|---|
| AC1 | PR créée uniquement après checkpoint/push propre | **PASS** |
| AC2 | Daemon ne tente plus d'agir sur le mauvais ticket/branche | **PASS** |
| AC3 | Fichiers projet normaux sont checkpointables | **PASS** |
| AC4 | Vrais fichiers inconnus bloquent toujours le daemon | **PASS** |
| AC5 | Fichiers runtime ne polluent plus Git | **PARTIAL PASS** |
| AC6 | Aucun `git add .` | **PASS** |

---

### Blocking Issue — Test regression introduced by T103

`tests/test_daemon_pr_lifecycle.py::test_checkpoint_and_push_before_pr_skips_push_when_nothing_to_commit` is **failing** because T103 changed the behavior of `_checkpoint_and_push_before_pr` (Bug 1 fix: always push prior commits), but the test was not updated. The test still asserts `push_calls == []`, which was the pre-T103 behavior. The test name and assertion both need updating to reflect the new contract.

**Fix needed** (`tests/test_daemon_pr_lifecycle.py:248`): change `assert push_calls == []` to `assert len(push_calls) == 1` (and rename the test).

---

### Non-Blocking Gaps

1. **AC5 partial**: 24 `runs/*/workflow-status.md` files (T003–T031) remain tracked in Git — pre-existing issue from main, plan only addressed `node_modules`. These are auto-checkpointed (start with `runs/`), not workflow-blocking, but violate the letter of the ticket.

2. **Pre-existing test failure**: `tests/test_commit_push.py::test_commit_with_include_code_stages_all_scope_paths` was already failing on main before T103 — out of scope.

**356 of 358 tests pass.** The 1 regression must be fixed before merge.
