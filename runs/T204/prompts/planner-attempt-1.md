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
document…", "Key points covered…", "The document now contains…".

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



# T204 — T204 - Add Ticket Operations panel for guarded manual recovery actions

**Source**: GitHub Issue #264

## Description

# T204 - Add Ticket Operations panel for guarded manual recovery actions

## Context

AI Dev Factory now has diagnostic capabilities for stuck tickets.

T203 explains why a ticket is stuck and recommends safe recovery actions, but it does not execute those actions.

The next step is to add a dedicated Ticket Operations panel where a human operator can trigger selected manual recovery actions with explicit safeguards.

This is an operator console for recovery, not an automation engine.

## Goal

Add a Ticket Operations panel to the ticket detail page that exposes guarded manual actions for recovering or managing a ticket.

The panel should use diagnostics as input when available and display only relevant actions.

Initial supported actions should be conservative and explicit.

## Non-goals

Do not:

- add automatic recovery
- dispatch new tickets
- change scheduler behavior
- change worker reservation behavior
- introduce parallel execution logic
- auto-delete anything without confirmation
- bypass human approval rules
- merge PRs automatically
- silently reset ticket state

## New concept

Create a service:

```text
tools/agent_runner/ticket_operations.py
```

It should expose guarded operations for a ticket.

Each operation must:

1. validate preconditions
2. return a structured result
3. write an audit log entry if an audit mechanism exists
4. avoid destructive changes unless explicitly confirmed
5. never run automatically

## Operation safety levels

Every operation must have a safety level:

```text
low
medium
high
destructive
```

Rules:

- `low` actions can run after a normal click confirmation.
- `medium` actions require a confirmation modal.
- `high` actions require typing the ticket id.
- `destructive` actions require typing the ticket id and a second explicit confirmation.

## Initial operations

### Re-run advisory analyzers

These actions are safe and should call the existing API/service flows:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
```

They should not mutate ticket execution state.

### Approval actions

Expose existing human approval actions:

```text
approve_execution
reject_execution
```

They must use the existing Human Approval Workflow and must not duplicate approval logic.

### Mark ticket blocked

Action:

```text
mark_blocked
```

Purpose:

Allow a human to mark a ticket as blocked with a reason.

Requirements:

- requires reason text
- appends or persists the blocking reason
- does not delete worktree
- does not cancel runs unless a separate action is explicitly triggered

### Reset ticket to planning

Action:

```text
reset_to_planning
```

Purpose:

Recover from a bad/stale/invalid plan.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous artifacts in an archive/history folder if possible
- must record why the reset happened
- must not delete the worktree by default
- must not run the planner automatically

### Reset ticket to coding

Action:

```text
reset_to_coding
```

Purpose:

Recover when implementation needs to be regenerated but the plan is still valid.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous code/review/test artifacts where possible
- must not delete plan artifacts
- must not run the coder automatically

### Clear stuck transient state

Action:

```text
clear_stuck_state
```

Purpose:

Clear stale transient runtime markers when no active worker/daemon is actually running.

Requirements:

- medium or high safety level depending on existing state
- must verify no active process/worker heartbeat exists before clearing
- must not touch artifacts or worktree
- must record what was cleared

### Delete ticket worktree

Action:

```text
delete_worktree
```

Purpose:

Remove a broken ticket worktree after a ticket is cancelled, reset, archived, or confirmed stuck.

Requirements:

- destructive safety level
- requires typed ticket id
- requires explicit confirmation
- refuses to run if a worker is active or if the worktree has uncommitted changes unless force is explicitly confirmed
- must never delete outside the configured worktrees root
- must record deleted path

### Archive ticket

Action:

```text
archive_ticket
```

Purpose:

Move a ticket out of the active workflow without deleting data.

Requirements:

- medium safety level
- requires reason text
- must preserve all artifacts
- should mark the ticket as archived/cancelled using existing board conventions if available

## API

Add Control API endpoints:

```text
GET /tickets/{ticket_id}/operations
POST /tickets/{ticket_id}/operations/{operation_key}
```

Project-scoped variants:

```text
GET /projects/{project_id}/tickets/{ticket_id}/operations
POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}
```

`GET` returns available operations for the current ticket:

```json
{
  "ticket_id": "T204",
  "operations": [
    {
      "operation_key": "rerun_diagnostics",
      "label": "Re-run diagnostics",
      "safety_level": "low",
      "enabled": true,
      "disabled_reason": null,
      "requires_reason": false,
      "requires_typed_ticket_id": false,
      "requires_double_confirmation": false
    }
  ]
}
```

`POST` executes one operation after validating confirmation payload.

Suggested request:

```json
{
  "reason": "Plan is stale after main changed",
  "typed_ticket_id": "T204",
  "confirm": true,
  "force": false
}
```

Suggested response:

```json
{
  "ticket_id": "T204",
  "operation_key": "reset_to_planning",
  "status": "completed",
  "message": "Ticket reset to planning and previous artifacts archived.",
  "details": {}
}
```

## Database / audit

Prefer using an existing audit log if available.

If no generic audit mechanism exists, add a lightweight table:

```text
ticket_operation_audit
```

Suggested fields:

```text
id
ticket_id
project_id
operation_key
status
reason
requested_by
details_json
created_at
```

Every operation attempt should be recorded, including rejected attempts.

## Frontend

Add a panel:

```text
Ticket Operations
```

Location:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
```

Suggested component:

```text
apps/dashboard/src/components/TicketOperationsPanel.jsx
```

Display:

- operation groups:
  - Advisory re-runs
  - Approval actions
  - Recovery actions
  - Dangerous actions
- enabled/disabled state
- disabled reason
- safety level badge
- confirmation modal
- reason input when required
- typed ticket id confirmation when required
- operation result message

If T203 diagnostics are available, display a small hint:

```text
Recommended by diagnostics
```

next to actions matching `recommended_actions`.

## Safety requirements

The operations service must be defensive.

It must:

- never delete outside the configured project/worktree roots
- verify paths with resolved absolute paths before deleting
- refuse destructive actions while a worker heartbeat is active
- require explicit confirmation payload for high/destructive actions
- record every attempted operation
- return clear errors instead of partially mutating state

## Tests

Add tests for:

- available operations API
- confirmation validation
- safety-level requirements
- rerun diagnostics operation
- approval operations delegate to existing approval service
- reset to planning preserves previous artifacts or records why it cannot
- clear stuck state refuses when active heartbeat exists
- delete worktree refuses outside worktrees root
- delete worktree refuses dirty worktree unless force confirmed
- archive ticket preserves artifacts
- audit log records successful and rejected operations
- UI renders operations grouped by safety level
- UI requires typed ticket id for high/destructive actions

## Acceptance criteria

- Ticket detail page displays a Ticket Operations panel.
- Available operations are returned by API with safety metadata.
- Low-risk advisory re-run operations can be triggered manually.
- Approval actions reuse the existing approval workflow.
- Recovery actions validate preconditions and confirmation requirements.
- Destructive actions are guarded by typed ticket id and explicit confirmation.
- Every operation attempt is audited.
- No operation runs automatically.
- Scheduler, dispatcher, worker allocation, and parallel execution remain unchanged.
- Existing tests continue to pass.