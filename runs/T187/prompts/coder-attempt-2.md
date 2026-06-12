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

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

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

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


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

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Clean build. Implementation is complete.

---

**Summary of changes:**

**New: `apps/dashboard/src/lib/ticketColumns.js`**
- `COLUMN_DEFS` — 4-column definitions with id, label, and Tailwind color tokens
- `STATE_TO_COLUMN` — maps every known state string to one of 4 column ids (unknown states fall back to `queued`)
- `columnForState(state)` — single-call helper
- `STATE_BADGE_COLORS` + `stateBadgeClass(state)` — centralized badge color logic (moved from the old page local constant)

**New: `apps/dashboard/src/components/TicketPreviewPanel.jsx`**
- Slide-in drawer (fixed right, `z-50`) with backdrop
- Shows: ticket id, state badge, branch, issue number, last activity timestamp, last log, last error (fetched via `getTicketTimeline` on open)
- Navigation footer: "Open ticket" (Link), "Open GitHub issue" (rendered only when `issue_number` + optional `githubRepo` prop are both set), "Open PR (see ticket detail)"
- Close via `×` button or click-outside

**Modified: `apps/dashboard/src/pages/ProjectTicketsPage.jsx`**
- Table replaced with 4-column flex-row Kanban board
- Each ticket is a clickable `TicketCard` button — no direct navigation, opens `TicketPreviewPanel` instead
- `waiting_human` column cards have `ring-2 ring-orange-400` highlight
- Preserves 5 s polling, `ErrorBanner`, and `usePolling` logic unchanged
- All local `STATE_COLORS` / `stateBadgeClass` constants removed; imported from `ticketColumns.js`

---

## Review

Now I have all the information needed. Let me write the structured review.

---

## Review — T187: Restore Ticket Board Workflow

### Ticket vs. Implementation

| Requirement | Status |
|---|---|
| 4-column Kanban board (Queued/Running/Waiting Human/Done) | ✅ |
| Centralized status-to-column mapping | ✅ |
| All 27+ known states mapped | ✅ |
| Unknown states fall to Queued | ✅ |
| Waiting Human column visually distinct | ✅ (orange ring on cards) |
| Click opens preview drawer | ✅ |
| Preview: ticket ID, state, branch | ✅ |
| Preview: latest activity (updated_at) | ✅ |
| Preview: latest log | ✅ |
| Preview: latest error (via timeline API) | ✅ |
| Preview: worktree path | ✅ (placeholder, plan-deferred) |
| Preview: linked PR | ✅ (placeholder, plan-deferred) |
| Preview: **ticket title** | ❌ missing — not in list API; plan excluded it but ticket requires it |
| Preview: linked GitHub issue (hyperlink) | ❌ broken — `githubRepo` prop never passed |
| Navigation: Open ticket | ✅ |
| Navigation: Open GitHub issue | ❌ button never renders (same cause) |
| Navigation: Open PR | ⚠️ always shown, even without PR — minor UX |
| Existing TicketDetailPage functional | ✅ |
| Multi-project / workspace preserved | ✅ |
| 5-second polling preserved | ✅ |

---

### Blocking issue — `githubRepo` never passed to `TicketPreviewPanel`

`ProjectTicketsPage.jsx:79-83` mounts the panel without the `githubRepo` prop:

```jsx
<TicketPreviewPanel
  ticket={previewTicket}
  projectId={projectId}
  // githubRepo not passed
  onClose={() => setPreviewTicket(null)}
/>
```

`TicketPreviewPanel.jsx` is correctly structured to use it — the prop is declared on line 6, the issue hyperlink is conditional on it at line 72, and the "Open GitHub issue" footer button is conditional at line 128. But because the parent never fetches or forwards project metadata, the prop is always `undefined`.

**Consequence**: GitHub issue links and "Open GitHub issue" button are never rendered, regardless of whether a ticket has an `issue_number`. The plan acceptance criterion explicitly states: *"Open GitHub issue link is visible and correct when issue_number is set."* This is unmet.

**Required fix**: `ProjectTicketsPage` must fetch the current project's metadata (which should include a `github_repo` field) and forward it. A `getProject(projectId)` call in a `useEffect` is sufficient — this does not require a backend change since the projects API already exists.

---

### Secondary gap — ticket title absent from preview

The ticket requirement lists "title" as a required preview field. The plan explicitly excluded it citing the list API not returning `title`. This exclusion is technically valid as a scope boundary, but it means the preview shows only the ticket ID as an identifier, which reduces usability — particularly for boards with many tickets.

This is not a blocker for this cycle given the plan's explicit carve-out, but the gap should be tracked and the list API / `TicketSummary` schema should be extended in a follow-up.

---

### Minor observations

- **"Open PR (see ticket detail)" is always shown** (line 138-144) regardless of whether a PR exists. Per plan this is acceptable as a placeholder, but the label is misleading for tickets that have no PR — "See ticket detail" alone would be clearer.
- **"Pull request" info row** (line 107-114) similarly always renders "See ticket detail." No blocking concern.
- **Timeline fetch errors** are silently collapsed to `null`, showing "none" with no indication of failure (line 20-21). Acceptable for MVP; a future improvement could distinguish "no error" from "fetch failed."
- **Column width fixed at `w-64`**: with many tickets in one column, vertical scroll within the column works correctly. No concern.

---

### Code quality

`ticketColumns.js` is clean and genuinely acts as a single source of truth. The `stateBadgeClass` fuzzy fallback (`state?.includes(k)`) is clever but mildly risky — a state like `TESTING_COMPLETE` would incorrectly match `TESTING`. Not a live bug given current states, but worth noting.

`TicketPreviewPanel.jsx` handles event listener cleanup correctly (line 31). Hook dependencies are correct. Loading/error states are handled.

`ProjectTicketsPage.jsx` is straightforward. The bucketing idiom on lines 32-35 is clean and performant for typical ticket counts.

---

### Summary

The implementation delivers a functional, well-structured Kanban board with good visual hierarchy and clean code. One acceptance criterion fails: the GitHub issue link infrastructure exists in `TicketPreviewPanel` but the parent never provides the `githubRepo` prop, so the feature is dead-wired. This requires a small but real fix — fetching and forwarding project metadata. The ticket title gap is documented and plan-deferred.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T187/reviews/implementation-review.md
- generated at: 2026-06-12T13:56:09Z

---

Now I have all the information needed. Let me write the structured review.

---

## Review — T187: Restore Ticket Board Workflow

### Ticket vs. Implementation

| Requirement | Status |
|---|---|
| 4-column Kanban board (Queued/Running/Waiting Human/Done) | ✅ |
| Centralized status-to-column mapping | ✅ |
| All 27+ known states mapped | ✅ |
| Unknown states fall to Queued | ✅ |
| Waiting Human column visually distinct | ✅ (orange ring on cards) |
| Click opens preview drawer | ✅ |
| Preview: ticket ID, state, branch | ✅ |
| Preview: latest activity (updated_at) | ✅ |
| Preview: latest log | ✅ |
| Preview: latest error (via timeline API) | ✅ |
| Preview: worktree path | ✅ (placeholder, plan-deferred) |
| Preview: linked PR | ✅ (placeholder, plan-deferred) |
| Preview: **ticket title** | ❌ missing — not in list API; plan excluded it but ticket requires it |
| Preview: linked GitHub issue (hyperlink) | ❌ broken — `githubRepo` prop never passed |
| Navigation: Open ticket | ✅ |
| Navigation: Open GitHub issue | ❌ button never renders (same cause) |
| Navigation: Open PR | ⚠️ always shown, even without PR — minor UX |
| Existing TicketDetailPage functional | ✅ |
| Multi-project / workspace preserved | ✅ |
| 5-second polling preserved | ✅ |

---

### Blocking issue — `githubRepo` never passed to `TicketPreviewPanel`

`ProjectTicketsPage.jsx:79-83` mounts the panel without the `githubRepo` prop:

```jsx
<TicketPreviewPanel
  ticket={previewTicket}
  projectId={projectId}
  // githubRepo not passed
  onClose={() => setPreviewTicket(null)}
/>
```

`TicketPreviewPanel.jsx` is correctly structured to use it — the prop is declared on line 6, the issue hyperlink is conditional on it at line 72, and the "Open GitHub issue" footer button is conditional at line 128. But because the parent never fetches or forwards project metadata, the prop is always `undefined`.

**Consequence**: GitHub issue links and "Open GitHub issue" button are never rendered, regardless of whether a ticket has an `issue_number`. The plan acceptance criterion explicitly states: *"Open GitHub issue link is visible and correct when issue_number is set."* This is unmet.

**Required fix**: `ProjectTicketsPage` must fetch the current project's metadata (which should include a `github_repo` field) and forward it. A `getProject(projectId)` call in a `useEffect` is sufficient — this does not require a backend change since the projects API already exists.

---

### Secondary gap — ticket title absent from preview

The ticket requirement lists "title" as a required preview field. The plan explicitly excluded it citing the list API not returning `title`. This exclusion is technically valid as a scope boundary, but it means the preview shows only the ticket ID as an identifier, which reduces usability — particularly for boards with many tickets.

This is not a blocker for this cycle given the plan's explicit carve-out, but the gap should be tracked and the list API / `TicketSummary` schema should be extended in a follow-up.

---

### Minor observations

- **"Open PR (see ticket detail)" is always shown** (line 138-144) regardless of whether a PR exists. Per plan this is acceptable as a placeholder, but the label is misleading for tickets that have no PR — "See ticket detail" alone would be clearer.
- **"Pull request" info row** (line 107-114) similarly always renders "See ticket detail." No blocking concern.
- **Timeline fetch errors** are silently collapsed to `null`, showing "none" with no indication of failure (line 20-21). Acceptable for MVP; a future improvement could distinguish "no error" from "fetch failed."
- **Column width fixed at `w-64`**: with many tickets in one column, vertical scroll within the column works correctly. No concern.

---

### Code quality

`ticketColumns.js` is clean and genuinely acts as a single source of truth. The `stateBadgeClass` fuzzy fallback (`state?.includes(k)`) is clever but mildly risky — a state like `TESTING_COMPLETE` would incorrectly match `TESTING`. Not a live bug given current states, but worth noting.

`TicketPreviewPanel.jsx` handles event listener cleanup correctly (line 31). Hook dependencies are correct. Loading/error states are handled.

`ProjectTicketsPage.jsx` is straightforward. The bucketing idiom on lines 32-35 is clean and performant for typical ticket counts.

---

### Summary

The implementation delivers a functional, well-structured Kanban board with good visual hierarchy and clean code. One acceptance criterion fails: the GitHub issue link infrastructure exists in `TicketPreviewPanel` but the parent never provides the `githubRepo` prop, so the feature is dead-wired. This requires a small but real fix — fetching and forwarding project metadata. The ticket title gap is documented and plan-deferred.

IMPLEMENTATION_FIX_REQUIRED