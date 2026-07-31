## Objective

Replace the fixed right-side panel of the AI Workspace with a floating, draggable, resizable window that can also be docked to the left or right side of the viewport. Mode, size, and position are persisted to `localStorage` and restored on page refresh, with dynamic clamping on restoration and viewport resize, and automatic bottom-drawer fallback on small screens.

## Included

**Dependency addition:**
- `apps/dashboard/package.json`: add `react-rnd` (handles draggable + resizable in floating mode).

---

**New hook — `apps/dashboard/src/hooks/useWorkspaceLayout.js`:**

Manages `{ mode, x, y, width, height }` under `localStorage` key `workspace_layout`.

- `mode` is one of `'floating' | 'docked-left' | 'docked-right'`.
- Defaults: `mode: 'floating'`, `width: 320`, `height: 600`, `x`/`y` centred in the current viewport.
- Enforces minimum dimensions: `minWidth = 280`, `minHeight = 400`.
- Enforces maximum dimensions computed from current viewport:
  - floating: `maxWidth = min(900, viewportWidth - 48)`, `maxHeight = viewportHeight - 48`.
  - docked: `maxWidth = min(800, viewportWidth - 320)`.
- On mount, restores values from `localStorage` and clamps `x`, `y`, `width`, `height` into the computed min/max bounds, correcting stale off-screen or oversized values.
- Registers a `resize` event listener on `window`; on each resize event, re-clamps the stored layout against the new viewport dimensions and updates state.
- Exports `{ layout, setMode, setPosition, setSize }`.

---

**Modified — `apps/dashboard/src/App.jsx` (`AppLayout` function):**

- Import and call `useWorkspaceLayout()`.
- When `workspaceOpen && layout.mode === 'docked-left'`, apply `style={{ marginLeft: layout.width }}` to `<main>`; for `'docked-right'`, apply `marginRight`. No margin when mode is `'floating'` or panel is closed.
- Pass `layout`, `setMode`, `setPosition`, `setSize` as additional props to `<ProjectWorkspacePanel>`.
- Render `<ProjectWorkspacePanel>` after `</main>` (outside the flex row), using `position: fixed` for all modes, so the panel never participates in flex layout.

---

**Refactored — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`:**

Props signature: `{ projectId, isOpen, onClose, layout, setMode, setPosition, setSize }`.

When `isOpen` is false, return `null` (component stays mounted in the tree so conversation state survives).

When `isOpen` is true, render according to `layout.mode` and screen width (tracked via a `resize` event listener):

**Small screen sub-mode (viewport width < 768 px):**
- Render a `<div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '60vh', zIndex: 50 }}>` regardless of stored mode.
- Mode-switcher buttons are hidden in this sub-mode.

**Floating mode (viewport ≥ 768 px):**
- Wrap panel UI in `<Rnd>` from `react-rnd` with:
  - `bounds="window"` (prevents off-screen dragging).
  - `minWidth={280}` / `minHeight={400}`.
  - `position={{ x: layout.x, y: layout.y }}` / `size={{ width: layout.width, height: layout.height }}`.
  - `onDragStop={(_, d) => setPosition({ x: d.x, y: d.y })}`.
  - `onResizeStop={(_, __, ref, ___, pos) => { setSize({ width: ref.offsetWidth, height: ref.offsetHeight }); setPosition(pos); }}`.
  - `dragHandleClassName="ws-drag-handle"` — applied only to the narrow drag-strip area in the header (not the full header).
  - `cancel="button, input, textarea, [data-no-drag]"` — prevents mode-switcher, close, and form controls from initiating a drag gesture.
  - `style={{ position: 'fixed', zIndex: 50 }}`.
  - `enableResizing` with all 8 handles enabled.

**Docked-left / docked-right mode (viewport ≥ 768 px):**
- Render a `<div style={{ position: 'fixed', top: 0, [side]: 0, height: '100vh', width: layout.width, zIndex: 40 }}>`.
- No drag in docked mode.
- A 4 px resize strip on the inner edge enables single-axis width resizing using Pointer Events:
  - `onPointerDown` on the strip: record pointer start position, call `e.currentTarget.setPointerCapture(e.pointerId)`, register `onPointerMove` and `onPointerUp`/`onPointerCancel` on the strip element.
  - `onPointerMove`: compute delta, clamp new width to `[minWidth, maxWidth]`, call `setSize`.
  - `onPointerUp` / `onPointerCancel`: release pointer capture and remove listeners.
  - On component unmount: release capture and remove listeners if a resize is in progress.
  - Supports mouse, touch, and pen input uniformly via Pointer Events API.

**Header structure (all non-small-screen modes):**
- A narrow `<div className="ws-drag-handle" style={{ cursor: 'grab' }}>` occupies the left portion of the header (≈ 24 px strip) and is the sole initiator of floating-mode drag.
- The remaining header area contains the project-name label (not draggable), then three icon-only mode buttons and the close button. All buttons carry `data-no-drag` and explicit `aria-label` attributes:
  - Float button: `aria-label="Switch to floating window"`, calls `setMode('floating')`.
  - Dock-left button: `aria-label="Dock to left side"`, calls `setMode('docked-left')`.
  - Dock-right button: `aria-label="Dock to right side"`, calls `setMode('docked-right')`.
  - Close button: `aria-label="Close workspace"`, calls `onClose`.
- Active mode button receives `ring-2 ring-blue-500` highlight.
- Clicks or pointer interactions on any button do not initiate a drag gesture (enforced by both the `cancel` prop on `<Rnd>` and `data-no-drag` attribute).

**Preserved unchanged:**
- All conversation state (`messages`, `input`, `loading`, `error`) and the three `useEffect` hooks managing scroll, focus, and project-switch reset.
- `handleSubmit`, `handleConfirmAction`, `handleConfirmIssue` logic.
- `ActionConfirmCard` and `IssueConfirmCard` sub-components.
- The input form and message list rendering.

**Not modified:**
- `apps/dashboard/src/components/ProjectSidebar.jsx` — toggle button interface unchanged.
- All files under `apps/dashboard/src/api/`.
- All page components and other hooks.
- Backend (no API changes needed).

## Excluded

- Multiple simultaneous workspace windows.
- Tabbed conversations.
- Multi-monitor specific layout or per-monitor position memory.
- Snap-to-edge animation or magnetic docking while dragging.
- Persistent conversation history across page refreshes (separate concern, not in this ticket).
- Any backend or API changes.

## Acceptance criteria

- The panel renders as a floating window (`position: fixed`, `z-index: 50`) when mode is `floating`.
- The panel can be dragged by grabbing the designated drag-handle strip in the header, and stays within viewport bounds (no off-screen drift).
- Clicking the float, dock-left, dock-right, and close buttons does not initiate a drag gesture.
- Every icon-only button has an explicit `aria-label` readable by screen readers.
- The panel can be resized from all 8 edges and corners in floating mode; it does not shrink below 280 × 400 px.
- In docked mode, the inner-edge resize strip responds to mouse, touch, and pen input (Pointer Events); pointer capture is released correctly on completion, cancellation, and unmount.
- Clicking dock-left or dock-right switches the panel to the respective side; `<main>` shifts by the panel width with no overlap.
- Clicking the float button switches back to the free-floating window.
- Mode, position, and size survive a hard page refresh (values restored from `localStorage` on mount, clamped to current viewport bounds).
- Stored layout values are re-clamped whenever the viewport is resized, preventing off-screen or oversized states.
- Switching modes or closing and reopening the panel does not clear the chat conversation.
- On viewport width < 768 px the panel ignores the stored mode and appears as a fixed bottom drawer (60 vh height, full width).
- All existing functionality works without regression: message send, action confirmation card, issue confirmation card, error display, auto-scroll, project-switch conversation reset.
