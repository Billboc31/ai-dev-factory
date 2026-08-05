# Plan review 01

## Decision

PLAN_FIX_REQUIRED

## Summary

The plan is well structured, but it must be regenerated before implementation to address input compatibility, layout bounds, and drag accessibility.

## Required changes

### 1. Use Pointer Events for docked resizing

Replace the planned mouse-only resize flow (`mousedown`, `mousemove`, `mouseup`) with:

- `pointerdown`
- `pointermove`
- `pointerup`
- `pointercancel`

The resize handle must support mouse, touch, and pen input. Pointer listeners must always be removed when resizing ends, when it is cancelled, and when the component unmounts.

### 2. Add dynamic maximum dimensions and clamp restored values

Define maximum width and height constraints for both floating and docked modes.

In docked mode, preserve a usable minimum width for the main content, for example:

```text
maxWidth = min(800px, viewportWidth - 320px)
```

Clamp all persisted layout values restored from `localStorage`:

- `width`
- `height`
- `x`
- `y`

Apply the clamp on initial restoration and again whenever the viewport size changes.

### 3. Prevent interactive header controls from starting a drag

Do not let clicks or pointer interactions on the float, dock-left, dock-right, and close controls initiate window dragging.

Use either a dedicated drag-handle area or a `react-rnd` cancel selector such as:

```jsx
cancel="button, input, textarea, [data-no-drag]"
```

Add an explicit `aria-label` to every icon-only action button.

## Expected regenerated plan

The regenerated `runs/T226/plan.md` must explicitly cover:

- Pointer Events for docked resizing;
- listener cleanup for completed and cancelled resizing;
- dynamic maximum dimensions;
- clamping of size and position after restoration and viewport resize;
- drag-safe interactive header controls;
- accessible labels for icon-only buttons.
