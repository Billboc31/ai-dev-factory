# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T187/reviews/implementation-review.md
- generated at: 2026-06-12T13:56:09Z

---

Now I have all the information needed. Let me write the structured review.

---

## Review — T187: Restore Ticket Board Workflow

### Ticket vs. Implementation

| Requirement | Status |
|---|---|
| 4-column Kanban board (Queued/Running/Waiting Human/Done) | ✅ |
| Centralized status-to-column mapping | ✅ |
| All 27+ known states mapped | ✅ |
| Unknown states fall to Queued | ✅ |
| Waiting Human column visually distinct | ✅ (orange ring on cards) |
| Click opens preview drawer | ✅ |
| Preview: ticket ID, state, branch | ✅ |
| Preview: latest activity (updated_at) | ✅ |
| Preview: latest log | ✅ |
| Preview: latest error (via timeline API) | ✅ |
| Preview: worktree path | ✅ (placeholder, plan-deferred) |
| Preview: linked PR | ✅ (placeholder, plan-deferred) |
| Preview: **ticket title** | ❌ missing — not in list API; plan excluded it but ticket requires it |
| Preview: linked GitHub issue (hyperlink) | ❌ broken — `githubRepo` prop never passed |
| Navigation: Open ticket | ✅ |
| Navigation: Open GitHub issue | ❌ button never renders (same cause) |
| Navigation: Open PR | ⚠️ always shown, even without PR — minor UX |
| Existing TicketDetailPage functional | ✅ |
| Multi-project / workspace preserved | ✅ |
| 5-second polling preserved | ✅ |

---

### Blocking issue — `githubRepo` never passed to `TicketPreviewPanel`

`ProjectTicketsPage.jsx:79-83` mounts the panel without the `githubRepo` prop:

```jsx
<TicketPreviewPanel
  ticket={previewTicket}
  projectId={projectId}
  // githubRepo not passed
  onClose={() => setPreviewTicket(null)}
/>
```

`TicketPreviewPanel.jsx` is correctly structured to use it — the prop is declared on line 6, the issue hyperlink is conditional on it at line 72, and the "Open GitHub issue" footer button is conditional at line 128. But because the parent never fetches or forwards project metadata, the prop is always `undefined`.

**Consequence**: GitHub issue links and "Open GitHub issue" button are never rendered, regardless of whether a ticket has an `issue_number`. The plan acceptance criterion explicitly states: *"Open GitHub issue link is visible and correct when issue_number is set."* This is unmet.

**Required fix**: `ProjectTicketsPage` must fetch the current project's metadata (which should include a `github_repo` field) and forward it. A `getProject(projectId)` call in a `useEffect` is sufficient — this does not require a backend change since the projects API already exists.

---

### Secondary gap — ticket title absent from preview

The ticket requirement lists "title" as a required preview field. The plan explicitly excluded it citing the list API not returning `title`. This exclusion is technically valid as a scope boundary, but it means the preview shows only the ticket ID as an identifier, which reduces usability — particularly for boards with many tickets.

This is not a blocker for this cycle given the plan's explicit carve-out, but the gap should be tracked and the list API / `TicketSummary` schema should be extended in a follow-up.

---

### Minor observations

- **"Open PR (see ticket detail)" is always shown** (line 138-144) regardless of whether a PR exists. Per plan this is acceptable as a placeholder, but the label is misleading for tickets that have no PR — "See ticket detail" alone would be clearer.
- **"Pull request" info row** (line 107-114) similarly always renders "See ticket detail." No blocking concern.
- **Timeline fetch errors** are silently collapsed to `null`, showing "none" with no indication of failure (line 20-21). Acceptable for MVP; a future improvement could distinguish "no error" from "fetch failed."
- **Column width fixed at `w-64`**: with many tickets in one column, vertical scroll within the column works correctly. No concern.

---

### Code quality

`ticketColumns.js` is clean and genuinely acts as a single source of truth. The `stateBadgeClass` fuzzy fallback (`state?.includes(k)`) is clever but mildly risky — a state like `TESTING_COMPLETE` would incorrectly match `TESTING`. Not a live bug given current states, but worth noting.

`TicketPreviewPanel.jsx` handles event listener cleanup correctly (line 31). Hook dependencies are correct. Loading/error states are handled.

`ProjectTicketsPage.jsx` is straightforward. The bucketing idiom on lines 32-35 is clean and performant for typical ticket counts.

---

### Summary

The implementation delivers a functional, well-structured Kanban board with good visual hierarchy and clean code. One acceptance criterion fails: the GitHub issue link infrastructure exists in `TicketPreviewPanel` but the parent never provides the `githubRepo` prop, so the feature is dead-wired. This requires a small but real fix — fetching and forwarding project metadata. The ticket title gap is documented and plan-deferred.

IMPLEMENTATION_FIX_REQUIRED
