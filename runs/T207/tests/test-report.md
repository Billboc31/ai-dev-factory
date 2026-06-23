## Validation: PASS

T207 implementation satisfies all 9 acceptance criteria.

**Test results**
- `pytest tests/test_ticket_operations.py tests/test_control_api_operations.py` → 37/37 pass
- `pytest tests/test_planner_recovery.py tests/test_run_ticket_clean_gate.py tests/test_fix_artifact.py` → 22/22 pass (no regression in fix-artifact path)

**Core fix verified**
- `_handle_reset_to_planning` writes `state="INIT"` (ticket_operations.py:363); `TRANSITIONS["INIT"] == ("planner", True, ["PLAN_REVIEW_NEEDED"])` is deterministic
- `_collect_fix_artifacts` is gated by `current_state in {"PLAN_FIX_REQUIRED", "IMPLEMENTATION_FIX_REQUIRED"}` at run_ticket.py:46, so state=`INIT` cannot trigger the original `fix artifact missing` error
- Symmetric bug in `_handle_reset_to_coding` also fixed (state=`PLAN_APPROVED`, `implementation-output.md` added to archived artifacts)

**Regressions**: none from T207. The 28 failures in `test_control_api_artifacts/endpoints/subprocess` are pre-existing test-isolation defects (verified identical on baseline `142b5867` — actually 30 there vs. 28 on T207).

Full report written to `runs/T207/tests/tester-report.md`.
