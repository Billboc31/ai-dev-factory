**Test report: PASS**

All 7 acceptance criteria are satisfied:

| AC | Result |
|---|---|
| Redeploy no longer fails when source scripts missing | PASS |
| Missing source clone automatically recreated | PASS |
| Correct branch/ref restored | PASS |
| Logs indicate clone rehydration (all 6 required lines) | PASS |
| Advanced runtime options collapsed by default | PASS |
| Force source refresh/reclone available | PASS |
| Runtime validation prevents cross-runtime path mismatches | PASS |

**Regressions:** None. The 1 test failure in scope (`test_create_environment_auto_creates_nested_custom_sandbox_path`) and all 65 failures in the broader suite are pre-existing on `main` — confirmed by running against the main branch clone.

Report written to `runs/T176/test-report.md`.
