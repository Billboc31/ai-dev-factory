## Objective

Replace the fixed right-side panel of the AI Workspace with a floating, draggable, resizable window that can also be docked to the left or right side of the viewport. Mode, size, and position are persisted to `localStorage` and restored on page refresh, with automatic bottom-drawer fallback on small screens.

## Included

**Dependency addition:**
- `apps/dashboard/package.json`: add `react-rnd` (handles draggable + resizable in floating mode, no extra build configuration required).

**New hook — `apps/dashboard/src/hooks/useWorkspaceLayout.js`:**
- Manages `{ mode, x, y, width, height }` under `localStorage` key `workspace_layout`.
- `mode` is one of `'floating' | 'docked-left' | 'docked-right'`.
- Defaults: `mode: 'floating'`, `width: 320`, `height: 600`, `x`/`y` centred in the current viewport.
- On mount, clamps stored `x`/`y` to current viewport bounds so stale off-screen positions are corrected automatically.
- Enforces `minWidth = 280`, `minHeight = 400` before writing to state.
- Exports `{ layout, setMode, setPosition, setSize }`.

**Modified — `apps/dashboard/src/App.jsx` (`AppLayout` function):**
- Import and call `useWorkspaceLayout()`.
- Apply `style={{ marginLeft: layout.width }}` to `<main>` when `workspaceOpen && layout.mode === 'docked-left'`, and `marginRight` for `'docked-right'`. No margin when mode is `floating` or the panel is closed.
- Pass `layout`, `setMode`, `setPosition`, `setSize` as additional props to `<ProjectWorkspacePanel>`.
- `ProjectWorkspacePanel` moves outside the flex-sibling row (rendered after `</main>`) and uses `position: fixed` for all modes, so its DOM position no longer affects flex layout; only the margins above do.

**Refactored — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`:**

Props signature: `{ projectId, isOpen, onClose, layout, setMode, setPosition, setSize }`.

When `isOpen` is false, return `null` (unchanged — React state is preserved since the component stays mounted).

When `isOpen` is true, render based on `layout.mode` and screen width:

- **Small screen sub-mode (viewport width < 768 px, tracked via a `resize` event listener):** render a `<div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '60vh', zIndex: 50 }}>` regardless of `layout.mode`. Mode-switcher buttons are hidden in this sub-mode.

- **Floating mode:** wrap the panel UI in `<Rnd>` from `react-rnd` with:
  - `bounds="window"` (prevents off-screen dragging).
  - `minWidth={280}` / `minHeight={400}`.
  - `position={{ x: layout.x, y: layout.y }}` / `size={{ width: layout.width, height: layout.height }}`.
  - `onDragStop={(_, d) => setPosition({ x: d.x, y: d.y })}`.
  - `onResizeStop={(_, __, ref, ___, pos) => { setSize({ width: ref.offsetWidth, height: ref.offsetHeight }); setPosition(pos) }}`.
  - `dragHandleClassName="ws-drag-handle"` — applied to the header `<div>` (same element that already has the title and close button).
  - `style={{ position: 'fixed', zIndex: 50 }}` via Rnd's `style` prop.
  - `enableResizing={{ top, bottom, left, right, topLeft, topRight, bottomLeft, bottomRight }}` (all 8 handles).

- **Docked-left / docked-right mode:** render a plain `<div style={{ position: 'fixed', top: 0, [side]: 0, height: '100vh', width: layout.width, zIndex: 40 }}>`. No drag. A 4 px drag strip on the inner edge allows width resizing via `onMouseDown` → `mousemove` → `mouseup` on `document` (no library needed for this single-axis resize).

**Header additions (all non-small-screen modes):**
- Add three icon buttons after the project-name label: float (⤢), dock-left (▐←), dock-right (→▌). Each calls `setMode('floating' | 'docked-left' | 'docked-right')`. Active mode gets a `ring-2 ring-blue-500` highlight.
- The header `<div>` receives `className="ws-drag-handle"` and `style={{ cursor: 'move' }}` so `react-rnd` knows which element initiates drag.

**Preserved unchanged:**
- All conversation state (`messages`, `input`, `loading`, `error`) and the three `useEffect` hooks that manage scroll, focus, and project-switch reset.
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
- The panel can be dragged by grabbing the header bar and stays within viewport bounds (no off-screen drift).
- The panel can be resized from all 8 edges and corners; it does not shrink below 280 × 400 px.
- Clicking dock-left or dock-right in the header switches the panel to the respective side; main content shifts by the panel width with no visual overlap.
- Clicking the float button switches back to the free-floating window.
- Mode, position, and size survive a hard page refresh (values restored from `localStorage` on mount).
- Switching modes or closing and reopening the panel does not clear the chat conversation.
- On viewport width < 768 px the panel ignores the stored mode and appears as a fixed bottom drawer (60 vh height, full width).
- All existing functionality works without regression: message send, action confirmation card, issue confirmation card, error display, auto-scroll, project-switch conversation reset.
