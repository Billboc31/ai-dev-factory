# Plan fix 01

## Ticket

T226 — Add floating and dockable AI Workspace window

## Source review

`runs/T226/reviews/plan-review-01.md`

## Decision

PLAN_FIX_REQUIRED

## Required plan corrections

### 1. Use Pointer Events for docked resizing

Replace the mouse-only docked resize flow with:

- `pointerdown`
- `pointermove`
- `pointerup`
- `pointercancel`

The implementation plan must support mouse, touch, and pen input. It must explicitly include listener cleanup when resizing completes, when it is cancelled, and when the component unmounts.

### 2. Add dynamic maximum dimensions and clamp persisted layout

The regenerated plan must define maximum dimensions for floating and docked modes.

For docked mode, preserve a usable minimum width for the main application content, for example:

```text
maxWidth = min(800px, viewportWidth - 320px)
```

Clamp every persisted layout value restored from `localStorage`:

- `width`
- `height`
- `x`
- `y`

The plan must apply this clamping both during initial restoration and after viewport resizing.

### 3. Keep interactive header controls outside the drag behavior

Clicks or pointer interactions on the float, dock-left, dock-right, and close buttons must not initiate dragging.

The regenerated plan must use either:

- a dedicated drag-handle area; or
- a `react-rnd` cancel selector such as:

```jsx
cancel="button, input, textarea, [data-no-drag]"
```

Every icon-only action button must also receive an explicit `aria-label`.

## Expected output

Regenerate `runs/T226/plan.md` so that it explicitly covers all corrections above. Do not implement application code as part of this plan-fix step.
