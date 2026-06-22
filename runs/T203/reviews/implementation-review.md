I've completed the review. Let me write it up as a structured PR review.

## Review

### Summary

T203 adds a read-only stuck-ticket diagnostic service. The implementation closely follows the plan and ticket spec: `tools/agent_runner/ticket_diagnostics.py` (1069 lines) implements `diagnose_ticket()` with 11 per-check helpers, a 15-key recommended-action catalog, dedup, and persistence; `services/control_api/routes/diagnostics.py` wires four endpoints (bare GET/POST + project-scoped variants); `runtime_db.py` / `runtime_db_pg.py` get a `ticket_diagnostics` table plus `upsert_ticket_diagnostics` / `get_ticket_diagnostics`; the `TicketDiagnosticsPanel.jsx` is mounted on `TicketDetailPage.jsx`. All 29 new Python tests pass and all 6 new Vitest tests pass.

### Correctness vs. ticket / plan

| Requirement | Status |
|---|---|
| `diagnose_ticket(db_path, project_root, ticket_id) -> dict` | ✅ Implemented with bounded timeout |
| 11 checks (existence, runtime, intelligence, readiness, approval, rules, worktree, branch, PR, logs, freshness) | ✅ All present |
| 15-action catalog with `{action_key, label, risk, reason}` | ✅ Matches ticket exactly (`tools/agent_runner/ticket_diagnostics.py:49`) |
| Dedup recommended actions, preserve order | ✅ Tested (`tools/agent_runner/ticket_diagnostics.py:78`) |
| Bounded subprocess (`timeout=timeout_s`) for all git calls | ✅ Centralized in `_safe_git` (`tools/agent_runner/ticket_diagnostics.py:97`) |
| `unknown` collapse on every failure path (never raises) | ✅ Verified by manual trace through each helper |
| GET 404 when no persisted row | ✅ `services/control_api/routes/diagnostics.py:122` |
| POST 404 when ticket missing in both DB and filesystem | ✅ `services/control_api/routes/diagnostics.py:153` |
| Project-scoped routes return same payload | ✅ Test `test_project_scoped_get_returns_same_payload` |
| DB table + JSON columns + immutable `created_at` | ✅ `test_created_at_preserved_across_updates` |
| Postgres parity | ✅ Mirrored in `runtime_db_pg.py` with composite PK + JSONB casts |
| Safety: no destructive imports/calls | ✅ Enforced by `test_ticket_diagnostics_safety.py` with explicit allow-list |
| Recommendation buttons rendered disabled with "Action not wired yet" | ✅ `TicketDiagnosticsPanel.jsx:182-194` |

### Scope compliance

The implementation is strictly read-only except for `runtime_db.upsert_ticket_diagnostics`. The safety test (`tests/test_ticket_diagnostics_safety.py`) enforces both an import blacklist and a runtime_db allow-list — those tripwires are the right shape for this ticket. No mutation of approvals, rules, runtime state, branches, PRs, worktrees, daemon, scheduler, or workers. No agent execution. ✅

### Observations (non-blocking)

1. **Check `details` not rendered in the UI** — `TicketDiagnosticsPanel.jsx:158-173` shows only `key` + status pill + `message`. The plan listed an "optional details block" for the checks list. The service puts useful payloads in `details` (full `blocking_reasons`, full `failed_rules`, `worktree_status`, `expected_path`, `current_main_sha`, last 20 lines of log…) — none of which surfaces to the user. The check `message` only includes the first blocking reason / first failed rule. A future iteration should render at least a collapsed details panel; the data is already on the wire.

2. **Run-button double round-trip** — `TicketDiagnosticsPanel.jsx:96-99` sets state from the POST response and then calls `fetchDiagnostics()` (a second GET). The POST already returns the persisted shape; the GET is redundant. Minor wasted request per click.

3. **`_resolve_project_id` silently returns invalid IDs** — `services/control_api/routes/diagnostics.py:59-64` falls back to the raw override on `ValueError`. A malformed `project_id` query parameter would be persisted as-is. Low risk because the catalog of routes that hit this is narrow, but worth tightening (raise 400 on invalid override).

4. **`_resolve_run_dir` duplicates `resolve_ticket_run_dir` semantics** — intentional per the plan ("avoid importing the Control API service module to keep this file as standalone as the rest of `tools/agent_runner`"), but it means edge cases (custom runs dir, non-default worktree layout) could disagree with the API's `get_ticket()`. Acceptable, just worth noting.

5. **Branch check doesn't recommend `reset_to_planning` for missing branches** — the ticket text says `missing branch with existing run → reset_ticket or recreate_branch`. The implementation emits only `recreate_branch` (`tools/agent_runner/ticket_diagnostics.py:636-639`). Defensible (less destructive), but a small deviation from the spec.

6. **Logs check only inspects `runtime.log`** — the plan suggested "bounded scan of `runs/<ticket_id>/`" returning the latest log filename. The implementation hard-codes `runtime.log` rather than scanning. Functionally sufficient for the current single-log layout, but the contract is slightly narrower than the ticket implies.

7. **`_check_runtime` never returns `failed`** — even if `state` is `FAILED` or `*_ERROR`, the runtime check returns `passed`. Downstream checks pick up the real blocker, but the runtime priority slot effectively never wins. Not wrong (the plan didn't define failure semantics for runtime), but conceptually weak.

### Code quality

- Module structure is clear: constants → helpers → per-check functions → priority/severity derivation → assembly → public entry point.
- Pure `build_diagnostic` extracted as the plan required, exercised by `test_build_diagnostic_assembles_structure`.
- No comments rotted or stale.
- Pydantic models match DB columns.
- `_dedupe_actions` preserves insertion order and the first occurrence's `reason`, as tested.

### Tests

Quality is good: edge cases (missing ticket, missing intelligence, blocked readiness, ready-candidate-without-approval, blocked rules, missing worktree, merged-PR-vs-unfinished-ticket, idempotency, persistence, dedup, pure-helper assembly) all covered. The safety tests are the most valuable — they make future "diagnostic surface grew teeth" regressions impossible without explicit allow-list edits. Vitest coverage hits healthy state, stuck state, disabled buttons, 404→empty state, POST→GET flow, and generated_at rendering.

### Decision

All ticket acceptance criteria are met. The observations above are improvements, not blockers. The diagnostic surface is read-only, bounded, deterministic, and tested with explicit tripwires preventing scope creep.

IMPLEMENTATION_APPROVED
