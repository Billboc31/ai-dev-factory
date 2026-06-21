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



# T200 — Add Human Approval Workflow and READY_TO_TAKE lifecycle

**Source**: GitHub Issue #256

## Description

# Add Human Approval Workflow and READY_TO_TAKE lifecycle

## Context

AI Dev Factory now has:

- Ticket Intelligence Analyzer
- Ticket Readiness Evaluator

The next step is to introduce a human approval workflow before tickets are allowed to enter execution.

The goal is to let users decide which tickets may actually be executed while keeping the current scheduler and execution pipeline unchanged.

This introduces a distinction between:

```text
READY_CANDIDATE
```

and:

```text
READY_TO_TAKE
```

A ticket may be technically ready but still require a human decision.

## Goals

Introduce a human approval workflow that allows:

- approving a ticket for execution
- revoking approval
- tracking approval history
- displaying approval status on the dashboard

This ticket does not start execution automatically.

## Lifecycle

New state:

```text
READY_TO_TAKE
```

Proposed lifecycle:

```text
Draft
↓
Ticket Intelligence
↓
Readiness Evaluator
↓
READY_CANDIDATE
↓
Human Approval
↓
READY_TO_TAKE
↓
Future Dispatcher
```

A ticket cannot become READY_TO_TAKE unless:

```text
readiness_status == ready_candidate
```

## Non-goals

Do not:

- automatically start execution
- modify worker scheduling
- dispatch tickets
- reorder queues
- implement reservation logic
- implement stale context checks
- automatically approve tickets

Those behaviors will come later.

## Database

Create:

```text
ticket_approval
```

Suggested fields:

```text
ticket_id
approval_status
approved_by
approved_at
revoked_by
revoked_at
approval_reason
created_at
updated_at
```

Suggested statuses:

```text
not_requested
ready_candidate
ready_to_take
revoked
```

Only one active approval row is required for now.

## Approval history

Create:

```text
ticket_approval_history
```

Suggested fields:

```text
id
ticket_id
action
actor
reason
created_at
```

Actions:

```text
approved
revoked
reapproved
```

## API

Add:

```text
GET /tickets/{ticket_id}/approval
POST /tickets/{ticket_id}/approve
POST /tickets/{ticket_id}/revoke-approval
```

Rules:

- approve returns 409 if ticket is not `ready_candidate`
- approving twice is idempotent
- revoking twice is idempotent

## Frontend

Add a new panel:

```text
Ticket Approval
```

Display:

- current approval status
- approver
- approval date
- reason
- history

Actions:

```text
Approve For Execution
Revoke Approval
```

When approved, display:

```text
READY TO TAKE
```

badge.

## Human workflow

This workflow is intentionally manual.

Future versions may allow:

- automatic approval policies
- low-risk ticket auto-approval
- rule-based approvals

Those are excluded from this ticket.

## Acceptance criteria

- Tickets can be approved only when `readiness_status == ready_candidate`.
- Approval status is persisted.
- Approval history is persisted.
- Approving twice is idempotent.
- Revoking twice is idempotent.
- Dashboard displays approval information and history.
- `READY_TO_TAKE` badge is visible when approved.
- Existing scheduler and execution pipeline remain unchanged.
- No ticket execution starts automatically.
- Existing test suite continues to pass.