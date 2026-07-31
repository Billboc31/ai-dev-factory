# Plan review

## Decision

PLAN_FIX_REQUIRED

## Required changes

### 1. Use Pointer Events for docked resizing

The docked resize handle must support mouse, touch and pen input. Replace the planned `mousedown` / `mousemove` / `mouseup` listeners with `pointerdown`, `pointermove`, `pointerup` and `pointercancel`.

Ensure listeners are always removed when resizing ends and when the component unmounts.

### 2. Add dynamic maximum dimensions and clamp restored values

The workspace currently defines minimum dimensions but no maximum dimensions.

Add dynamic limits for floating and docked modes. In docked mode, preserve a usable minimum width for the main content, for example:

```text
maxWidth = min(800px, viewportWidth - 320px)
```

Clamp all values restored from `localStorage`, including:

- width
- height
- x
- y

The clamp must run on mount and after viewport resizing.

### 3. Prevent toolbar buttons from starting a drag

The complete header must not behave as a drag handle when the user interacts with the float, dock or close buttons.

Use either a dedicated drag area or configure `react-rnd` with a cancel selector such as:

```jsx
cancel="button, input, textarea, [data-no-drag]"
```

Add explicit accessible labels to all icon-only controls, including float, dock left, dock right and close.

## Validation expected in the regenerated plan

The regenerated `plan.md` must explicitly describe:

- Pointer Events for docked resizing;
- cleanup of resize listeners;
- dynamic maximum dimensions;
- clamping after restoration and viewport resize;
- protection of interactive header controls from drag initiation;
- accessible labels for icon-only buttons.
