# T230 — Batch UI: show per-ticket pipeline status while batch is frozen/waiting

**Source**: GitHub Issue #317

## Description

## Problem
When a backlog batch is `frozen`, the UI mostly shows the batch status alone. That status is not self-explanatory: `frozen` means “collection stopped”, not “dependency analysis running”.

Operators cannot see **which tickets are blocking the next stage** (e.g. Ticket Intelligence still `running` on T003–T006), so a batch looks stuck for no visible reason.

## Expected UX
On the batch detail / batch list view, show a clear per-ticket breakdown of what each member is doing and what the batch is waiting on.

For each ticket in the batch, surface at least:
- ticket id + title/issue number
- Ticket Intelligence status (`not_started` / `queued` / `running` / `completed` / `failed`)
- Readiness status (when applicable)
- runtime state (INIT, PLANNING, …)
- a short “blocking reason” when the batch cannot advance

At batch level, show an explicit waiting summary, e.g.:
- `Waiting on Ticket Intelligence: T003, T004, T005, T006`
- or `Ready for dependency analysis`
- or `Dependency analysis running`
- or `Waiting on readiness: …`

## Why
`frozen` is a gate before `dependency_analysis_running`. Without per-ticket visibility, the IHM feels stuck and operators restart daemons / open issues unnecessarily.

## Acceptance criteria
- [ ] Batch IHM shows per-ticket intelligence / readiness / runtime status for all batch members
- [ ] While status is `frozen`, UI explains that collection is closed and which tickets still block dependency analysis
- [ ] When all intelligence is complete, UI clearly transitions messaging toward dependency analysis (and shows analysis progress/errors if any)
- [ ] Empty/missing pipeline rows are shown as not started, not hidden

## Notes
Related lifecycle: `collecting → frozen → dependency_analysis_running → readiness_running → dispatching → completed`.
Gate today: `batch_intelligence_complete()` requires every member `analysis_status == completed` before analysis starts.
