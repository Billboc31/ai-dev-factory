All conflicts are resolved. Here's a summary:

---

**Conflict resolved: `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`**

The file had a `UU` (both-sides-modified) conflict between:
- **main branch**: added floating/dockable panel layout — `react-rnd`, `Rnd` component, `FloatIcon`/`DockLeftIcon`/`DockRightIcon`, layout mode switching and resize handle
- **T227 branch**: added `getDeploymentStatus` import, `STAGE_LABELS`, redeploy confirmation card (project/branch/pull/components/dirty-warning table), deployment spinner, and 15-minute polling loop

**Decision**: Preserve both sides in full — the changes are entirely orthogonal. The dock/float layout wraps the outer panel container; the redeploy card and polling live inside `ActionConfirmCard` and `handleConfirmAction`. Neither side modifies the other's code.

The working tree file had already been correctly merged by a prior resolver pass (no conflict markers). This pass verified the content, staged the file, and updated `resolution.md`.

**`tests/test_conflict_resolver.py`** and **`tools/agent_runner/run_conflict_resolver.py`** (listed in the original context) were already clean — no `UU` status in the index.
