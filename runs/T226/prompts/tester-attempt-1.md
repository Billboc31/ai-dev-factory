# Tester Report — T226: Add floating and dockable AI Workspace window

**Date:** 2026-07-31  
**Branch:** ticket/T226-add-floating-and-dockable-ai-workspace-window

---

## Summary

All 6 acceptance criteria **PASS**. The implementation is functionally correct. Two pre-existing test failures exist (unrelated to T226). No dedicated unit tests were added for the new components.

**Verdict: VALIDATION PASSED**

---

## Acceptance Criteria

### AC1 — The AI Workspace can be moved freely

**PASS**

- Floating mode uses `react-rnd` (`Rnd` component) with `bounds="window"` — prevents off-screen dragging.
- Drag is restricted to a 24 px `ws-drag-handle` strip in the header. Interactive controls (`button`, `input`, `textarea`, `[data-no-drag]`) are excluded via the `cancel` prop.
- `onDragStop` saves the new `{ x, y }` position into `useWorkspaceLayout` state, which is immediately persisted to `localStorage`.

### AC2 — The window can be resized interactively

**PASS**

- **Floating mode:** `react-rnd` provides 8-directional resizing. `onResizeStop` updates both size and position.
- **Docked mode:** A 4 px inner-edge handle uses the Pointer Events API (`setPointerCapture`, `onPointerMove`, `onPointerUp`). Width is constrained to `[280px, min(800px, viewportWidth − 320px)]`. Height resize is not offered in docked mode (panels fill full viewport height, which is correct).
- Minimum dimensions enforced identically in both `useWorkspaceLayout.js` (`MIN_WIDTH=280`, `MIN_HEIGHT=400`) and `ProjectWorkspacePanel.jsx`.

### AC3 — Users can dock and undock the workspace

**PASS**

- Three mode buttons in the header: Float (`FloatIcon`), Dock Left (`DockLeftIcon`), Dock Right (`DockRightIcon`). Hidden on small screens (<768 px viewport width).
- Active mode is visually indicated with `ring-2 ring-blue-500`.
- `setMode()` calls `clampLayout()`, which recalculates valid dimensions for the new mode.
- Switching float → docked and back restores the previous floating position (clamped to viewport bounds).
- Conversation state is preserved across mode switches: the component stays mounted during mode changes (mode is a prop that changes value, not a remount).

### AC4 — Position and dimensions are restored after a page refresh

**PASS**

- `useWorkspaceLayout` saves the complete `{ mode, width, height, x, y }` object to `localStorage` key `workspace_layout` on every layout change via a `useEffect`.
- On mount, the `useState` initialiser reads from `localStorage` and clamps the result to current viewport bounds before using it.
- A window `resize` listener in the hook re-clamps layout whenever the viewport is resized.

### AC5 — Navigation inside AI Dev Factory does not reset the workspace

**PASS**

- `ProjectWorkspacePanel` is rendered **outside** the `<Routes>` tree, as a direct sibling of `<main>` in `AppLayout` (`App.jsx:129-139`). It is never unmounted by route changes.
- When `isOpen=false`, the component returns `null` (early return) but remains **mounted** in the React tree — `messages`, `input`, and `error` state are preserved.
- Navigating between pages of the same project (Tickets → Dashboard → Logs → …) has no effect on workspace state or conversation.
- Switching to a **different project** resets the conversation (`useEffect` on `projectId`, `ProjectWorkspacePanel.jsx:108-112`). This is intentional and correct.

### AC6 — The experience remains responsive and accessible

**PASS**

- Viewport < 768 px: renders as a fixed bottom drawer (`height: 60vh`), mode switcher buttons are hidden, input remains functional.
- Viewport resize reclamped in real time (both hook and component register `resize` listeners that clean up on unmount).
- All icon-only buttons carry `aria-label` attributes: `"Switch to floating window"`, `"Dock to left side"`, `"Dock to right side"`, `"Close workspace"`.
- Controls are native `<button>` elements — keyboard accessible by default.
- Docked resize handle sets `touchAction: 'none'` and accepts pointer events uniformly (mouse, touch, pen).

---

## Build & Test Results

### Build

```
vite build — 337 modules transformed, 0 errors
```

### Test suite (25 files)

| File | Result |
|---|---|
| tests/ticketWorkflowStatus.test.js | ✅ 29/29 |
| tests/api.test.js | ✅ 17/17 |
| tests/BatchDependencyGraph.test.jsx | ✅ 5/5 |
| tests/usePolling.test.js | ✅ 7/7 |
| tests/RuntimeStatusPanel.test.jsx | ✅ 5/5 |
| tests/BatchAnalysisSummaryPanel.test.jsx | ✅ 6/6 |
| tests/TicketWorkflowTimeline.test.jsx | ✅ 10/10 |
| **tests/ProjectSidebar.test.jsx** | **✅ 7/7** |
| tests/TicketList.test.jsx | ✅ 6/6 |
| tests/ProjectRouting.test.jsx | ✅ 5/5 |
| tests/TicketDiagnosticsPanel.test.jsx | ✅ 6/6 |
| tests/BatchesPage.test.jsx | ✅ 9/9 |
| tests/DaemonPage.test.jsx | ✅ 10/10 |
| tests/ProjectRulesPanel.test.jsx | ✅ 6/6 |
| tests/T187TicketBoard.test.jsx | ✅ 22/22 |
| tests/BatchDetailPage.test.jsx | ✅ 7/7 |
| tests/TicketOperationsPanel.test.jsx | ✅ 6/6 |
| tests/TicketDetailPage.test.jsx | ✅ 6/6 |
| tests/TicketIntelligencePanel.test.jsx | ✅ 27/27 |
| tests/TicketDetail.test.jsx | ✅ 9/9 |
| tests/QuotaAlertBanner.test.jsx | ✅ 2/2 |
| tests/TicketRuleEvaluationPanel.test.jsx | ✅ 9/9 |
| tests/ProjectDashboardPage.test.jsx | ✅ pass |
| tests/DaemonActivityFeed.test.jsx | ❌ **1 failure — pre-existing** |
| tests/RuntimeDashboardPage.test.jsx | ❌ **4 failures — pre-existing** |

### Pre-existing failures (not from T226)

**DaemonActivityFeed — 1 failure**  
`passes custom lines count to API` — API call argument mismatch. Component last modified in commit `b05c901c` (T125). Test last modified in commit `10420d38` (T030). Unrelated to T226.

**RuntimeDashboardPage — 4 failures**  
Tests assert section label `"Sandbox Runs"` but the component renders `"Proposal Runs"`. Component last modified in commit `598a7562` (T139). Unrelated to T226.

Neither failure was introduced or worsened by the T226 commits.

---

## Observations (non-blocking)

### No unit tests for new T226 files

No dedicated test files were added for:
- `src/hooks/useWorkspaceLayout.js`
- `src/components/ProjectWorkspacePanel.jsx`
- The "AI Workspace" toggle button added to `ProjectSidebar`

The existing `ProjectSidebar.test.jsx` passes (7/7) because no assertion targets the new workspace button.

**Recommended follow-up:** Add unit tests for `useWorkspaceLayout` (localStorage persistence, clampLayout logic, mode transitions) and a smoke test for `ProjectWorkspacePanel` (open/close, mode switch, projectId change clears messages).

---

## Commands Executed

```bash
# dependency check
ls node_modules | grep rnd           # react-rnd present

# build
npm run build                        # exit 0, 337 modules

# test suite
npx vitest run --reporter=verbose    # exit 1 (5 pre-existing failures)
```
