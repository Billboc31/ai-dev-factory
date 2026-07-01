# Test report — T220

**Verdict: VALIDATED.** All six acceptance criteria pass. Full report written to `runs/T220/tests/test-report.md`.

## Summary

| Criterion | Status |
|---|---|
| Foundation tickets detected reliably | PASS |
| Execution phases respect dependency ordering | PASS |
| No conflicting tickets in same phase | PASS |
| Implicit architectural dependencies inferred | PASS |
| Graph internally consistent for Dispatcher | PASS |
| Tests updated + realistic scenario | PASS |

## Test runs

- `pytest tests/test_global_dependency_analyzer.py -v` → **13 passed** in 0.13s, including `test_realistic_test_ai_dev_backlog` which reproduces the exact bad case from the ticket (T001 in phase 1 alongside T010 while marked conflicting) and asserts resolution via the `role` step.
- Wider suite (`-k "backlog or dispatcher or dependency or intelligence"`) → 244 passed; 3 failures + 2 errors in `test_ticket_intelligence_api.py` / `test_supervisor_intelligence_analyze.py`. I verified these reproduce identically with the T220 files restored to `main` — they are pre-existing and unrelated to this ticket.

## Blocking issues

None. The two minor non-blocking items (dead-code snapshot at analyzer.py:554/611, unused coherence-notes return) were already noted by the reviewer and don't affect correctness.
