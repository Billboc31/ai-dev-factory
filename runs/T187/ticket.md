# T187 — T187 - Restore ticket board workflow with status columns and ticket preview

**Source**: GitHub Issue #224

## Description

# Objective

The recent workspace/project changes made the ticket workflow less efficient.

Restore a ticket-first operational experience while keeping the new workspace and multi-project architecture.

---

# Problems observed

Current ticket display is less usable than the previous board.

Missing:

- clear ticket status columns
- quick ticket inspection
- quick navigation to ticket details
- fast review workflow

---

# Required UX

## Ticket board

Display tickets in four columns:

### Queued

States such as:
- QUEUED
- READY
- PLANNED

### Running

States such as:
- IMPLEMENTING
- TESTING
- REVIEWING
- ACTIVE execution states

### Waiting human

States such as:
- PLAN_REVIEW_NEEDED
- IMPLEMENTATION_REVIEW_NEEDED
- CONFLICT_RESOLUTION_NEEDED
- any explicit human-gate state

### Done

States such as:
- TEST_COMPLETE
- COMPLETED
- MERGED
- ARCHIVED

Status mapping must be centralized and easy to extend.

---

# Ticket preview

Clicking a ticket must open a preview panel (drawer or side panel preferred).

Preview should show:

- ticket id
- title
- current state
- branch name
- worktree path (if available)
- latest activity
- latest error (if available)
- linked PR (if available)
- linked GitHub issue

---

# Navigation actions

From preview:

- Open ticket page
- Open GitHub issue
- Open pull request (if present)
- Open worktree (future integration placeholder acceptable)

---

# Constraints

- Preserve existing workspace/project architecture
- Preserve multi-project support
- Do not remove current ticket detail pages
- Do not redesign deployment/runtime systems
- Focus on workflow efficiency

---

# Acceptance criteria

- Tickets are displayed in Queued / Running / Waiting human / Done columns
- Human-gate tickets are immediately visible
- Clicking a ticket opens a preview panel
- Preview contains ticket metadata and navigation links
- Existing ticket pages still work
- Workspace and multi-project features remain functional
