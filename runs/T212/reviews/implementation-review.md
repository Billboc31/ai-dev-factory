Review written to `runs/T212/reviews/implementation-review.md`.

**Summary**

The T212 implementation correctly delivers a read-only advisory `TicketDispatcherService` with four modes (`off`/`advisory`/`manual`/`auto`), opt-in via `AI_DEV_FACTORY_DISPATCHER_MODE`, defaulting to `off`. The read-only contract is structurally enforced and verified by a byte-equality DB snapshot test plus a grep-based test that forbids importing the runner/daemon/supervisor. All 20 new tests pass and adjacent eligibility/intelligence suites continue to pass.

**Non-blocking observations**
- No README/doc update for the dispatcher (plan asked for one).
- No `DispatcherPage` frontend smoke test, and `ProjectSidebar.test.jsx` / `ProjectRouting.test.jsx` weren't extended for the new nav entry.
- `_resolve_mode("")` (empty `?mode=`) returns `off` instead of falling back to the env-var mode — minor UX edge case.
- Excluded-state list (`PLANNING/CODING/CANCELLED/TEST_COMPLETE` + `daemon_archived`) is narrower than the plan's wording; mid-pipeline states land in `blocked` rather than being hidden.
- Linear eligibility scan per request × 10s polling — acceptable for advisory scope, worth tracking for the future scheduler.

**Decision**: IMPLEMENTATION_APPROVED
