## Summary

Fix applied for IMPLEMENTATION_FIX_REQUIRED. The four pieces of the T206 polling-halt safety mechanism are restored in `apps/dashboard/src/components/TicketIntelligencePanel.jsx`, byte-for-byte matching `main`:

1. **Constant**: `MAX_CONSECUTIVE_POLL_ERRORS = 5` re-added next to `POLL_INTERVAL`.
2. **State**: `pollErrorCount` state, reset on success, on 404, and on `ticketId/projectId` change; incremented on non-404 errors.
3. **Derivation/guard**: `pollingHalted = pollErrorCount >= MAX_CONSECUTIVE_POLL_ERRORS` AND-gated into `isActive` so the polling-interval drops to `null` and the analyze button re-enables.
4. **Banner JSX**: red "Polling halted — server unreachable…" line, placed right after the `err` line, before `loading`.

### Files modified
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` — restored polling-halt only; no T205 UI logic touched.

### Verifications
- `npx vitest run tests/TicketIntelligencePanel.test.jsx`: **25/25 pass** (same count as before the fix — no test churn, as the reviewer predicted).

### Non-blocking items (not addressed)
- **`node_modules/.vite/vitest/results.json`**: This repo commits the entire `node_modules/` tree (confirmed via `git ls-files`), so removing only this one regenerated cache file would be cosmetic and inconsistent with the project's vendored-deps convention. Left as-is given its non-blocking status.
- **Hide `Show detailed analysis` when every sub-field is empty**: Out of scope for the blocking fix; can be a separate touch-up if desired.

### Limits / assumptions
- The fix is a pure restoration — same identifiers, same comment, same banner copy and placement as `main` — so any downstream test that exercises polling-halt behavior will see identical semantics to T206.
