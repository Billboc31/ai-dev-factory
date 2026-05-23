All clean. Here's a summary of every change made:

**Blocking fix (required before merge):**
- `apps/dashboard/src/pages/TicketDetailPage.jsx:131–133` — Removed the false retry hint ("click Resolve Conflicts") from the `CONFLICT_RESOLUTION_FAILED` message. Replaced with "Manual intervention is required before this ticket can proceed."

**Non-blocking issues also addressed:**
- `services/control_api/routes/tickets.py` — Moved `import threading` to module-level; removed the 4 inline occurrences inside route functions.
- `tools/agent_runner/conflict_context_collector.py:9` — Corrected the docstring: context is captured before rebase, so there are no conflict markers in the file at write time.
- `tests/test_conflict_resolver.py` — Added 4 missing assertions covering `CONFLICT_RESOLVING` and `CONFLICT_RESOLVED_REVIEW_NEEDED` in `VALID_STATES`, `AUTO_RUNNABLE_STATES`, and `HUMAN_GATE_STATES`.
- `tools/agent_runner/run_daemon.py:141` — Added `CONFLICT_RESOLVED_REVIEW_NEEDED` to `HUMAN_GATE_STATES` (real production gap: the daemon could have incorrectly tried to auto-run a ticket awaiting human review of a conflict resolution).
