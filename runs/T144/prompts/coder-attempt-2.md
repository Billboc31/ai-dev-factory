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


# T144 — T144 — Conflict resolver agent and review UI

**Source**: GitHub Issue #138

## Description

Goal: add the conflict resolver agent that resolves detected PR conflicts inside the existing ticket worktree, then exposes the result through a dedicated dashboard review flow.

Context:
T143 detects PR conflicts, persists conflict metadata, and surfaces conflict state in the dashboard.

T144 is the next step: run a resolver agent with full ticket context, update the conflicted branch safely, and require human review before the workflow resumes.

Target workflow:
- ticket is in CONFLICT_RESOLUTION_NEEDED
- user clicks Resolve Conflicts in the dashboard
- resolver runs in the existing ticket worktree
- resolver collects ticket context
- resolver rebases or merges latest main into the ticket branch
- resolver fixes conflicts
- relevant tests run
- branch is pushed with force-with-lease
- ticket moves to CONFLICT_RESOLVED_REVIEW_NEEDED
- dashboard shows resolution summary, logs, changed files, tests and review actions

Scope:
- add workflow states:
  - CONFLICT_RESOLVING
  - CONFLICT_RESOLVED_REVIEW_NEEDED
- add resolver execution step in the ticket worktree
- collect context for the resolver:
  - ticket.md
  - plan.md
  - reviews
  - fixes
  - conflict metadata
  - PR diff
  - merge-base diff
  - conflicted files
  - latest main changes
- add dedicated resolver role/prompt
- run resolver via existing configured AI runtime
- resolve conflicts by editing files in the ticket worktree
- run relevant tests after resolution
- write resolver artifacts:
  - conflict/context.md
  - conflict/resolution.md
  - conflict/test-report.md
- commit resolution changes and artifacts
- push the PR branch with force-with-lease
- add dashboard UI:
  - Resolve Conflicts button
  - resolving status
  - resolver logs
  - conflicted files
  - changed files
  - test result
  - resolution summary
  - approve/reject review gate
- add API endpoints for starting resolver and approving/rejecting resolution

Safety rules:
- do not resolve conflicts in main
- do not reset the branch
- do not blindly choose ours/theirs
- do not auto-merge to main
- require human review after resolution
- preserve both ticket intent and latest main behavior when possible
- all changes happen inside the ticket worktree

Out of scope:
- global multi-branch dependency planning
- automatic merge to main
- production deployment conflict handling
- semantic ticket tree planning

Acceptance:
- user can launch conflict resolution from dashboard
- resolver runs in the existing ticket worktree
- resolver receives full ticket and conflict context
- resolved branch is pushed with force-with-lease
- resolver artifacts are persisted
- dashboard shows status, summary, changed files and tests
- human approve/reject gate is required before workflow resumes
- failure ends in CONFLICT_RESOLUTION_FAILED with logs

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation is complete. Here's a summary of everything that was built:

---

**Files created (5 new):**
- `ai/roles/conflict-resolver.md` — Role definition for the AI conflict resolver
- `prompts/generic/conflict-resolver.md` — Generic task prompt template
- `tools/agent_runner/conflict_context_collector.py` — Assembles ticket.md, plan.md, reviews, PR diff, merge-base diff, conflicted files into `conflict/context.md`
- `tools/agent_runner/run_conflict_resolver.py` — Executor: fetch → rebase → AI resolver → stage → continue rebase → tests → commit → push `--force-with-lease` → state transition

**Files modified (10):**
- `tools/agent_runner/run_ticket.py` — Added `CONFLICT_RESOLVING` + `CONFLICT_RESOLVED_REVIEW_NEEDED` to `VALID_STATES`, added `reject-conflict-resolution` to `HUMAN_APPROVAL_TRANSITIONS`, added `apply_approve_conflict_resolution()`, added `--approve/reject-conflict-resolution` CLI flags
- `tools/agent_runner/run_step.py` — Registered `conflict-resolver` in aliases, default outputs, role files, skill files
- `services/control_api/models/schemas.py` — Added `resolution_summary` and `conflict_test_result` to `TicketSummary`
- `services/control_api/services/artifact_reader.py` — Updated `_conflict_fields()` to read `conflict/resolution.md` and `conflict/test-report.md`; added new states to `_STATUS_MAP`
- `services/control_api/services/subprocess_runner.py` — Added `resolve_conflicts()`, `approve_conflict_resolution()`, `reject_conflict_resolution()`
- `services/control_api/routes/tickets.py` — Added 3 endpoints (`/resolve-conflicts`, `/approve-conflict-resolution`, `/reject-conflict-resolution`) + 3 project-scoped variants + `_transition_to_resolving()` helper
- `apps/dashboard/src/api/tickets.js` — Added `resolveConflicts`, `approveConflictResolution`, `rejectConflictResolution`
- `apps/dashboard/src/pages/TicketsPage.jsx` — Added yellow/blue badge styles for `CONFLICT_RESOLVING`/`CONFLICT_RESOLVED_REVIEW_NEEDED`; expanded `CONFLICT_STATES` set
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Added `ConflictResolutionPanel` component with state-conditional UI for all 4 conflict states
- `tests/test_human_approval.py` — Updated count/keys assertions to include new `reject-conflict-resolution` entry

---

## Review

Now I have everything needed to write the full review.

---

# Review — T144: Conflict Resolver Agent and Review UI

## Ticket Compliance

### States

All four required states are implemented: `CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLUTION_FAILED`. State transitions are consistent across `run_ticket.py`, `run_daemon.py`, and `run_conflict_resolver.py`.

### Resolver execution

`run_conflict_resolver.py` correctly:
- validates current branch is never `main` before any git operation
- validates branch matches state.json
- fetches origin, rebases onto `origin/main`
- on conflict: invokes the AI agent with composed prompt
- stages resolved files, continues rebase
- runs tests after resolution
- commits artifacts, pushes with `--force-with-lease`
- transitions to `CONFLICT_RESOLVED_REVIEW_NEEDED` on success, `CONFLICT_RESOLUTION_FAILED` on any failure

All 10 failure points are handled explicitly and log to `conflict/error.log`.

### Context collection

`conflict_context_collector.py` assembles ticket.md, plan.md, reviews, fixes, PR diff, merge-base diff, latest main commits, and conflicted file contents — matching the ticket spec exactly.

Note on ordering: context.md is written **before** `git rebase` starts, so the "Conflicted Files" section in context.md shows pre-rebase content without conflict markers. The module docstring says "with conflict markers preserved" — this is inaccurate. In practice the AI agent reads the actual in-worktree files (which do have markers after the failed rebase), so the resolver works correctly, but the docstring is misleading.

### Artifacts

`conflict/context.md`, `conflict/resolution.md`, and `conflict/test-report.md` are all written correctly.

### API endpoints

All required endpoints are present for both `/tickets/{id}/*` and `/projects/{pid}/tickets/{id}/*` routes:
- `POST resolve-conflicts` (202, background thread)
- `POST approve-conflict-resolution`
- `POST reject-conflict-resolution`
- `POST mark-conflict-failed`

The `_transition_to_resolving()` helper correctly prevents double-triggering by atomically moving state to `CONFLICT_RESOLVING` before spawning the background thread.

### Approve / Reject gate

Approve restores `pre_conflict_state` (resuming the workflow). Reject returns to `CONFLICT_RESOLUTION_NEEDED` (allowing a retry). Human gate is enforced. Satisfies acceptance criteria.

### Dashboard UI

`ConflictResolutionPanel` renders correctly for all four conflict states. Conflict metadata (detected at, pre-conflict state, conflicted files) is displayed. Approve/Reject buttons appear only in `CONFLICT_RESOLVED_REVIEW_NEEDED`. This matches the ticket spec.

---

## Blocking Issues

### 1. Misleading retry message for `CONFLICT_RESOLUTION_FAILED`

`TicketDetailPage.jsx:131–135`:

```jsx
{state === 'CONFLICT_RESOLUTION_FAILED' && (
  <p className="text-xs text-red-700 font-medium">
    Resolution failed. Check the logs tab for details. You may retry by clicking
    "Resolve Conflicts" after manually verifying the worktree state.
  </p>
)}
```

**Problem:** `CONFLICT_RESOLUTION_FAILED` is a terminal state with no outgoing transitions (verified by `test_conflict_resolution_failed_has_no_outgoing_transitions`). The "Resolve Conflicts" button only appears in `CONFLICT_RESOLUTION_NEEDED` state — it is **never rendered** when the ticket is in `CONFLICT_RESOLUTION_FAILED`. The message actively misleads the user: they will look for a button that does not exist.

**Required fix:** Either (a) remove the retry hint and replace it with an accurate message directing users to investigate logs, or (b) add an explicit escape-hatch transition from `CONFLICT_RESOLUTION_FAILED` → `CONFLICT_RESOLUTION_NEEDED` with a corresponding "Retry" button.

Option (b) would require adding a `reset-conflict-failure` endpoint and an outgoing transition from `CONFLICT_RESOLUTION_FAILED`, which is a scope extension. Option (a) is minimal and correct.

---

## Minor Observations (non-blocking)

### 2. Test coverage gap for intermediate conflict states

`tests/test_conflict_resolver.py` tests `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED` in `VALID_STATES`, `AUTO_RUNNABLE_STATES`, and `HUMAN_GATE_STATES`, but does not cover `CONFLICT_RESOLVING` or `CONFLICT_RESOLVED_REVIEW_NEEDED`. Both states are defined and used correctly in production code, but their state classification is untested. Adding four assertions would close the gap.

### 3. `import threading` inside route handler

`tickets.py:321` and `:578` both do `import threading` inline inside the route function body. Should be moved to module-level imports.

### 4. Misleading module docstring in `conflict_context_collector.py`

Line 9: `"full content of each conflicted file (with conflict markers preserved)"` — as noted above, context is captured before the rebase attempt, so no conflict markers are present at write time. The comment at line 186 (`"before rebase so we capture current conflicted files"`) is more accurate. The module docstring should be corrected to avoid confusion during maintenance.

### 5. Resolver does not assert state is `CONFLICT_RESOLVING` before executing

`run_conflict_resolver.py` reads `branch` from `state.json` but does not assert `state == "CONFLICT_RESOLVING"`. In API-triggered paths the API route pre-transitions the state, so this is fine in practice. As a direct CLI invocation guard, a check here would prevent accidental misuse. Low risk given current call paths.

---

## Safety Rules Verification

| Rule | Status |
|---|---|
| Never resolve conflicts on main | ✅ hard check at line 157 |
| Never reset the branch | ✅ no `git reset --hard` anywhere |
| No blind ours/theirs | ✅ AI agent role explicitly forbids this |
| No auto-merge to main | ✅ approval gate required |
| Force-with-lease only | ✅ `--force-with-lease` used |
| Human review required | ✅ CONFLICT_RESOLVED_REVIEW_NEEDED gate |
| All changes inside ticket worktree | ✅ subprocess CWD is resolved to ticket worktree |

---

## Summary

The implementation is architecturally correct and satisfies the ticket requirements. All safety rules are respected. The one blocking issue is a misleading UI message in the failed state that tells users to click a button that doesn't exist. This must be corrected before merge.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T144/reviews/implementation-review.md
- generated at: 2026-05-23T17:21:32Z

---

Now I have everything needed to write the full review.

---

# Review — T144: Conflict Resolver Agent and Review UI

## Ticket Compliance

### States

All four required states are implemented: `CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLUTION_FAILED`. State transitions are consistent across `run_ticket.py`, `run_daemon.py`, and `run_conflict_resolver.py`.

### Resolver execution

`run_conflict_resolver.py` correctly:
- validates current branch is never `main` before any git operation
- validates branch matches state.json
- fetches origin, rebases onto `origin/main`
- on conflict: invokes the AI agent with composed prompt
- stages resolved files, continues rebase
- runs tests after resolution
- commits artifacts, pushes with `--force-with-lease`
- transitions to `CONFLICT_RESOLVED_REVIEW_NEEDED` on success, `CONFLICT_RESOLUTION_FAILED` on any failure

All 10 failure points are handled explicitly and log to `conflict/error.log`.

### Context collection

`conflict_context_collector.py` assembles ticket.md, plan.md, reviews, fixes, PR diff, merge-base diff, latest main commits, and conflicted file contents — matching the ticket spec exactly.

Note on ordering: context.md is written **before** `git rebase` starts, so the "Conflicted Files" section in context.md shows pre-rebase content without conflict markers. The module docstring says "with conflict markers preserved" — this is inaccurate. In practice the AI agent reads the actual in-worktree files (which do have markers after the failed rebase), so the resolver works correctly, but the docstring is misleading.

### Artifacts

`conflict/context.md`, `conflict/resolution.md`, and `conflict/test-report.md` are all written correctly.

### API endpoints

All required endpoints are present for both `/tickets/{id}/*` and `/projects/{pid}/tickets/{id}/*` routes:
- `POST resolve-conflicts` (202, background thread)
- `POST approve-conflict-resolution`
- `POST reject-conflict-resolution`
- `POST mark-conflict-failed`

The `_transition_to_resolving()` helper correctly prevents double-triggering by atomically moving state to `CONFLICT_RESOLVING` before spawning the background thread.

### Approve / Reject gate

Approve restores `pre_conflict_state` (resuming the workflow). Reject returns to `CONFLICT_RESOLUTION_NEEDED` (allowing a retry). Human gate is enforced. Satisfies acceptance criteria.

### Dashboard UI

`ConflictResolutionPanel` renders correctly for all four conflict states. Conflict metadata (detected at, pre-conflict state, conflicted files) is displayed. Approve/Reject buttons appear only in `CONFLICT_RESOLVED_REVIEW_NEEDED`. This matches the ticket spec.

---

## Blocking Issues

### 1. Misleading retry message for `CONFLICT_RESOLUTION_FAILED`

`TicketDetailPage.jsx:131–135`:

```jsx
{state === 'CONFLICT_RESOLUTION_FAILED' && (
  <p className="text-xs text-red-700 font-medium">
    Resolution failed. Check the logs tab for details. You may retry by clicking
    "Resolve Conflicts" after manually verifying the worktree state.
  </p>
)}
```

**Problem:** `CONFLICT_RESOLUTION_FAILED` is a terminal state with no outgoing transitions (verified by `test_conflict_resolution_failed_has_no_outgoing_transitions`). The "Resolve Conflicts" button only appears in `CONFLICT_RESOLUTION_NEEDED` state — it is **never rendered** when the ticket is in `CONFLICT_RESOLUTION_FAILED`. The message actively misleads the user: they will look for a button that does not exist.

**Required fix:** Either (a) remove the retry hint and replace it with an accurate message directing users to investigate logs, or (b) add an explicit escape-hatch transition from `CONFLICT_RESOLUTION_FAILED` → `CONFLICT_RESOLUTION_NEEDED` with a corresponding "Retry" button.

Option (b) would require adding a `reset-conflict-failure` endpoint and an outgoing transition from `CONFLICT_RESOLUTION_FAILED`, which is a scope extension. Option (a) is minimal and correct.

---

## Minor Observations (non-blocking)

### 2. Test coverage gap for intermediate conflict states

`tests/test_conflict_resolver.py` tests `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED` in `VALID_STATES`, `AUTO_RUNNABLE_STATES`, and `HUMAN_GATE_STATES`, but does not cover `CONFLICT_RESOLVING` or `CONFLICT_RESOLVED_REVIEW_NEEDED`. Both states are defined and used correctly in production code, but their state classification is untested. Adding four assertions would close the gap.

### 3. `import threading` inside route handler

`tickets.py:321` and `:578` both do `import threading` inline inside the route function body. Should be moved to module-level imports.

### 4. Misleading module docstring in `conflict_context_collector.py`

Line 9: `"full content of each conflicted file (with conflict markers preserved)"` — as noted above, context is captured before the rebase attempt, so no conflict markers are present at write time. The comment at line 186 (`"before rebase so we capture current conflicted files"`) is more accurate. The module docstring should be corrected to avoid confusion during maintenance.

### 5. Resolver does not assert state is `CONFLICT_RESOLVING` before executing

`run_conflict_resolver.py` reads `branch` from `state.json` but does not assert `state == "CONFLICT_RESOLVING"`. In API-triggered paths the API route pre-transitions the state, so this is fine in practice. As a direct CLI invocation guard, a check here would prevent accidental misuse. Low risk given current call paths.

---

## Safety Rules Verification

| Rule | Status |
|---|---|
| Never resolve conflicts on main | ✅ hard check at line 157 |
| Never reset the branch | ✅ no `git reset --hard` anywhere |
| No blind ours/theirs | ✅ AI agent role explicitly forbids this |
| No auto-merge to main | ✅ approval gate required |
| Force-with-lease only | ✅ `--force-with-lease` used |
| Human review required | ✅ CONFLICT_RESOLVED_REVIEW_NEEDED gate |
| All changes inside ticket worktree | ✅ subprocess CWD is resolved to ticket worktree |

---

## Summary

The implementation is architecturally correct and satisfies the ticket requirements. All safety rules are respected. The one blocking issue is a misleading UI message in the failed state that tells users to click a button that doesn't exist. This must be corrected before merge.

IMPLEMENTATION_FIX_REQUIRED