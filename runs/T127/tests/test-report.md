**TEST_COMPLETE** — report written to `runs/T127/test-report.md`.

---

## Results

**18/18 new tests pass. 0 regressions.**

| Criterion | Status |
|---|---|
| AC1: Scan from dashboard | ✅ PASS |
| AC2: Deploy profile generated and stored | ⚠️ PARTIAL — stored ✅, generated ❌ (deferred V2) |
| AC3: Dashboard shows deployment actions | ✅ PASS (scan only, per V1 scope) |
| AC4: Deterministic Python deployment | ⏳ DEFERRED V2 |
| AC5: Deployment logs visible | ⏳ DEFERRED V2 |
| AC6: Healthchecks after deployment | ⏳ DEFERRED V2 |
| AC7: ai-dev-factory profile completeness | ✅ PASS — docker ✅, host daemon ✅, gh ✅, claude ✅ |
| AC8: Structured error returns | ✅ PASS (within V1 scope) |

**Blocking issues**: none. ACs 4–6 and the "generation" half of AC2 are explicitly deferred per the approved V1 plan — not regressions or bugs. The 44 pre-existing test failures are baseline noise unrelated to T127.
