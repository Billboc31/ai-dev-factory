# Test Report — T122 — Dashboard action audit trail

## Summary

**Result: PASS** — All 5 acceptance criteria are satisfied. No regressions in the T122-affected modules.

---

## Acceptance Criteria

### AC1 — Every action endpoint inserts exactly one audit row with `event_type` prefixed `"action:"`

**Status: PASS**

Verified that all 9 action endpoints call `_log_action()` immediately after executing the subprocess:

| Endpoint | `_log_action` call |
|---|---|
| `POST /tickets/{id}/approve-plan` | `"approve-plan"` |
| `POST /tickets/{id}/request-plan-fix` | `"request-plan-fix"` |
| `POST /tickets/{id}/approve-implementation` | `"approve-implementation"` |
| `POST /tickets/{id}/request-implementation-fix` | `"request-implementation-fix"` |
| `POST /tickets/{id}/run-next` | `"run-next"` |
| `POST /tickets/{id}/commit` | `"commit"` |
| `POST /tickets/{id}/push` | `"push"` |
| `POST /tickets/{id}/checkpoint` | `"checkpoint"` |
| `POST /tickets/{id}/archive` | `"archive"` |

Storage layer confirmed correct via DB integration test: `append_runtime_event()` inserts rows with `event_type="action:<name>"`, metadata serializes correctly, and audit log failures are non-fatal (wrapped in try/except).

**Limitation (non-blocking):** `run-next` dispatches the subprocess in a background thread and logs `ok=True, message="run-next dispatched in background"` immediately. The actual subprocess outcome is never captured in the audit log. This is an expected architectural constraint of the async design; the plan specifies `run-next` is fire-and-forget.

---

### AC2 — `GET /tickets/{ticket_id}/audit-log` returns only action-prefixed rows for that ticket, ordered by `created_at` descending

**Status: PASS**

- Endpoint exists: `@router.get("/{ticket_id}/audit-log", response_model=list[AuditEvent])`
- Filters events by `event_type.startswith("action:")` — non-action events excluded
- Ticket isolation confirmed: events for T001 and T002 are correctly separated
- Ordering: `ORDER BY id DESC` (auto-increment IDs are chronological, so functionally equivalent to `created_at DESC`)

---

### AC3 — Dashboard ticket detail page has an "Audit" tab with columns: timestamp, action, status

**Status: PASS**

- `"audit"` is in the `TABS` array in `TicketDetailPage.jsx`
- Tab renders `<AuditLog ticketId={id} />` when active
- `AuditLog.jsx` renders a `<table>` with four columns: **Timestamp**, **Action**, **Status**, **Message**
- Status badge renders green "ok" or red "error" based on `metadata.ok`
- Action column strips the `"action:"` prefix from `event_type`
- Empty state renders `"No audit events yet."` rather than an empty table

---

### AC4 — After triggering an action, refreshing the Audit tab shows the new event without a page reload

**Status: PASS**

`AuditLog.jsx` uses `useEffect([ticketId])` which triggers a fresh `getAuditLog()` fetch each time the component mounts. The component is conditionally rendered:

```jsx
{tab === 'audit' ? <AuditLog ticketId={id} /> : ...}
```

Switching to the Audit tab always unmounts and remounts the component, fetching the latest events — no browser page reload required.

**Limitation (non-blocking):** If the user is already on the Audit tab when an action button is triggered, the list does not auto-refresh. The user must click another tab and return to the Audit tab to see the new event. A polling mechanism or callback-driven refresh was not part of the plan scope.

---

### AC5 — `AuditEvent` Pydantic schema validates; endpoint returns HTTP 200 with empty list when no events exist

**Status: PASS**

Schema validation confirmed:
```python
AuditEvent(id=1, event_type="action:approve-plan", message="approve-plan ok",
           metadata={"ok": True, "returncode": 0}, created_at="2026-05-21T12:00:00Z")
# → valid

AuditEvent(id=2, event_type="action:archive", message="archive failed: error",
           metadata=None, created_at="2026-05-21T12:01:00Z")
# → valid (optional metadata)
```

Empty list case: `get_audit_log()` calls `_get_or_404()` first (404 if ticket does not exist), then returns `[]` with HTTP 200 when the ticket exists but has no audit events. Confirmed via DB integration test.

---

## Test Execution

### Commands run

```
python -m pytest tests/test_runtime_db.py -v
# → 15 passed in 0.05s

python -c "...runtime_db integration test..."
# → Empty list for unknown ticket: []
# → Total events for T001: 4, action events: 3
# → Order: archive → run-next → approve-plan (most recent first)
# → T001 events: 4, T002 events: 1
# → All DB tests PASSED

python -c "...AuditEvent schema validation test..."
# → AuditEvent schema validation: PASSED

python -c "...verify _log_action present in all 9 endpoints..."
# → PASS: all 9 actions

python -c "...verify endpoint signature and frontend columns..."
# → PASS: endpoint, filter, all 3 required columns, re-fetch on ticketId
```

### Regression check

Pre-existing failures in `test_control_api_artifacts.py`, `test_control_api_endpoints.py`, `test_ticket_timeline.py`, and `test_run_daemon.py` confirmed to exist on `main` before T122 — not regressions.

T122-affected module tests: **15/15 passed**.

---

## Blocking Issues

None.

---

## Non-blocking Observations

1. **`run-next` audit accuracy**: The audit always records `ok=True` for `run-next` since the background thread outcome is not tracked. Acceptable per design; the plan explicitly makes `run-next` fire-and-forget.
2. **No auto-refresh on same-tab action**: Audit tab only re-fetches on mount (tab switch), not on action completion while already on the tab. Out of scope per plan.
3. **Ordering by `id` vs `created_at`**: The DB query orders by `id DESC` rather than `created_at DESC`. These are functionally identical under normal operation (auto-increment IDs are monotonically chronological). The spec wording is satisfied in practice.
