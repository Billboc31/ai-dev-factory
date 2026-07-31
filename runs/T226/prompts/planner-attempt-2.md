# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Planner

## Mission

Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.

## Tu dois

- comprendre le ticket
- proposer les étapes minimales
- lister les fichiers à créer ou modifier
- identifier les risques
- expliciter le hors scope
- produire un plan Markdown versionnable
- signaler les hypothèses nécessaires

## Tu ne dois pas

- coder
- réécrire le ticket
- anticiper les tickets suivants
- élargir le scope
- masquer les incertitudes

## Sortie attendue

Un fichier de plan conforme à `ai/templates/plan-template.md`.

## Règles

- le plan doit rester court
- le plan doit être exécutable par un Coder sans ambiguïté
- toute hypothèse doit être explicite
- toute dérive de scope doit être refusée

## Structure obligatoire

Tout plan doit contenir au minimum **les sections suivantes** (titres
Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :

| Français (recommandé)         | English equivalent       |
|-------------------------------|--------------------------|
| `## Contexte`                 | `## Context`             |
| `## Objectif`                 | `## Objective`           |
| `## Inclus`                   | `## Included`            |
| `## Hors scope`               | `## Excluded`            |
| `## Critères d'acceptation`   | `## Acceptance criteria` |

Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.

Ces titres sont obligatoires même si une section est courte : un ticket
trivial peut produire un plan court, mais la structure doit rester stable.

Ne jamais produire uniquement un résumé.
Ne jamais produire un compte rendu d’implémentation.

## Interdictions absolues

Tu ne dois jamais écrire :
- "implémentation terminée"
- "syntaxe valide"
- "changements appliqués"
- "voici ce qui a été fait"

Tu dois produire uniquement un plan futur, pas un compte rendu passé.

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: architecture-discipline

# Skill — Architecture Discipline

## Objectif

Préserver la cohérence architecture du projet dans le temps.

## Règles

- respecter les invariants documentés
- éviter les couplages implicites
- éviter les dépendances inutiles
- éviter les refactors transversaux non demandés
- documenter toute nouvelle règle structurante
- privilégier les changements locaux et bornés

## Refuser si

- le scope dérive
- plusieurs couches sont modifiées sans justification
- des conventions existantes sont cassées
- la mémoire projet devient incohérente

---

# SKILL: documentation

# Skill — Documentation

## Objectif

Maintenir une documentation utile, concise et alignée avec le code réel.

## Règles

- documenter les décisions importantes
- éviter les documentations vagues
- garder la mémoire projet cohérente
- expliciter les invariants architecture
- préférer Markdown simple et versionnable

## Refuser si

- la documentation diverge du comportement réel
- la mémoire contient des suppositions non validées
- des décisions importantes ne sont pas tracées

---

# TASK

The ticket follows.
# Generic Planner Task Read the ticket below and produce a detailed implementation plan.

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…",
"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".

Do not use the Write tool on `plan.md` and then print a status summary —
your stdout IS the artifact. If you do write the file, stdout must still
be the full plan (same four headings), not a report about it.

## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
## Objective
## Included
## Excluded
## Acceptance criteria
These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
markdown
## Objective
Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
naming convention. Behaviour is preserved.

## Included
- `utils.py`: rename `foo` → `bar`, update the docstring.
- `tests/test_utils.py`: update the single import and assertion.

## Excluded
- Renaming callers in other modules (tracked in a follow-up ticket).
- Any logic change inside `foo` / `bar`.

## Acceptance criteria
- `utils.py` no longer defines `foo`.
- `pytest tests/test_utils.py` passes.
- No other file references the old name.

The ticket follows.



# T226 — Add floating and dockable AI Workspace window

**Source**: GitHub Issue #310

## Description

## Objective

Enhance the AI Workspace by replacing the fixed chat panel with a movable, resizable and dockable window, providing an IDE-like experience.

## Context

The AI Workspace should remain available while navigating through the project, but users should be free to organize their workspace according to their preferences.

## Requirements

- Support a floating window mode.
- Allow drag & drop using the window header.
- Allow resizing from edges and corners.
- Support docking to the left and right sides.
- Allow switching back to floating mode at any time.
- Preserve the current conversation while changing modes.
- Persist the selected mode, size and position between sessions.
- Prevent the window from being moved completely off-screen.
- Define sensible minimum dimensions.
- Adapt automatically to smaller screens (drawer or full-screen mode).
- Ensure the workspace remains available across project navigation.

## Acceptance criteria

- The AI Workspace can be moved freely.
- The window can be resized interactively.
- Users can dock and undock the workspace.
- Position and dimensions are restored after a page refresh.
- Navigation inside AI Dev Factory does not reset the workspace.
- The experience remains responsive and accessible.

## Out of scope

- Multiple simultaneous workspace windows.
- Tabbed conversations.
- Multi-monitor specific behaviors.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T226/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

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

---

## Review

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

---

## Instructions de fix

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