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



# T203 — T203 - Add stuck ticket diagnostics and recommended recovery actions

**Source**: GitHub Issue #262

## Description

# T203 - Add stuck ticket diagnostics and recommended recovery actions

## Context

AI Dev Factory now has several advisory/control layers around the ticket lifecycle:

- Ticket Intelligence
- Ticket Readiness Evaluator
- Human Approval Workflow
- Execution Rules Engine

As the system becomes more autonomous, tickets can get stuck for many reasons:

- waiting for human plan review
- waiting for execution approval
- failed readiness evaluation
- failed rules evaluation
- stale worktree
- missing branch
- missing PR
- failed planner/coder/reviewer/tester step
- daemon stopped
- worker reserved but no visible progress
- logs/artifacts missing
- state in DB inconsistent with filesystem state

Users need a clear diagnostic panel to understand why a ticket is stuck and what recovery actions are recommended.

This ticket should not execute destructive recovery actions directly. It only diagnoses, explains, and recommends.

Actual recovery buttons/actions can be implemented separately or wired later through the Ticket Operations panel.

## Goal

Add a stuck ticket diagnostic capability that analyzes a ticket and returns:

- current ticket state
- current run state
- worker / daemon reservation state if available
- readiness status
- approval status
- rule evaluation status
- worktree status
- branch status
- PR status
- last known step
- last error
- latest logs summary
- whether main moved since the last planning/code step, if data exists
- likely stuck reason
- recommended safe recovery actions

## Non-goals

Do not:

- delete tickets
- delete worktrees
- reset ticket state
- cancel active runs
- retry agents automatically
- change scheduler behavior
- change worker reservation behavior
- enforce stale-context gates
- auto-dispatch another ticket

This ticket is diagnostic only.

## New concept

Create a diagnostic service:

```text
tools/agent_runner/ticket_diagnostics.py
```

It should expose:

```python
diagnose_ticket(db_path, project_root, ticket_id) -> dict
```

The result should be deterministic and safe to call repeatedly.

## Diagnostic output

Suggested JSON shape:

```json
{
  "ticket_id": "T203",
  "diagnostic_status": "completed",
  "is_stuck": true,
  "severity": "warning",
  "summary": "Ticket is waiting for human approval.",
  "current_state": "WAITING_APPROVAL",
  "last_known_step": "plan_review",
  "last_error": null,
  "checks": [
    {
      "key": "readiness",
      "status": "passed",
      "message": "Ticket readiness is ready_candidate."
    },
    {
      "key": "approval",
      "status": "failed",
      "message": "Execution approval is missing."
    }
  ],
  "recommended_actions": [
    {
      "action_key": "approve_execution",
      "label": "Approve execution",
      "risk": "low",
      "reason": "Ticket passed readiness and rules but requires human approval."
    }
  ],
  "generated_at": "2026-06-22T12:00:00Z"
}
```

## Checks to implement

### Ticket existence

Verify the ticket exists in the current project board/filesystem/DB.

If missing:

```text
is_stuck = true
severity = error
recommended action = inspect project board / refresh tickets
```

### Runtime/run state

Collect available run information from the existing runtime DB and/or run artifacts.

Include:

- active run id if available
- current run status
- last step
- last transition time
- last error if available

### Intelligence status

Load Ticket Intelligence result if available.

Report:

- missing
- queued
- running
- completed
- failed

Recommended actions:

- missing/failed → `rerun_intelligence`
- queued/running for too long → `inspect_logs`

### Readiness status

Load Ticket Readiness result if available.

Recommended actions:

- missing/failed → `rerun_readiness`
- blocked → surface blocking reasons
- ready_candidate → continue checks

### Human approval status

Load approval state using the existing approval service.

Use:

```python
ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)
```

Do not duplicate approval lifecycle logic.

Recommended actions:

- ready_candidate but not ready_to_take → `approve_execution` or `reject_execution`
- rejected → show rejection reason if available

### Rules evaluation status

Load latest Execution Rules evaluation if available.

Recommended actions:

- missing/failed/stale → `rerun_rules`
- blocked → show failed rules and reasons
- eligible → continue checks

### Worktree status

Check whether the ticket worktree exists.

Report:

- exists
- missing
- dirty
- clean
- unknown

Recommended actions:

- missing while run expects it → `reset_to_planning` or `recreate_worktree`
- dirty and ticket failed unexpectedly → `inspect_worktree`

### Branch status

Check whether the ticket branch exists locally or can be detected from available Git metadata.

Report:

- exists
- missing
- unknown

Recommended actions:

- missing branch with existing run → `reset_ticket` or `recreate_branch`

### PR status

If PR metadata is available, report:

- no_pr
- open
- merged
- closed_unmerged
- unknown

Recommended actions:

- open PR → `open_pr`
- merged PR but ticket not marked done → `sync_ticket_state`
- closed unmerged → `reset_to_planning` or `archive_ticket`

### Logs/artifacts status

Collect a compact summary from existing run artifacts:

- latest log file path
- latest log timestamp
- last error line if available
- plan/review/test artifact presence

Do not parse huge logs aggressively. Use bounded reads.

### Stale context hints

If plan/code artifacts contain or expose a main SHA, compare it to current main SHA.

If no SHA is available, report:

```text
context_freshness = unknown
```

This ticket must not enforce stale-context blocking. It only reports the signal.

## Recommended action catalog

Return recommended actions as structured objects.

Initial action keys:

```text
rerun_intelligence
rerun_readiness
rerun_rules
approve_execution
reject_execution
inspect_logs
inspect_worktree
open_pr
reset_to_planning
reset_to_coding
recreate_worktree
recreate_branch
sync_ticket_state
archive_ticket
manual_investigation
```

Each action must include:

```text
action_key
label
risk
reason
```

Risk values:

```text
low
medium
high
destructive
```

This ticket only returns recommendations. It does not execute them.

## API

Add Control API endpoints:

```text
GET /tickets/{ticket_id}/diagnostics
POST /tickets/{ticket_id}/diagnostics/run
```

Project-scoped variants:

```text
GET /projects/{project_id}/tickets/{ticket_id}/diagnostics
POST /projects/{project_id}/tickets/{ticket_id}/diagnostics/run
```

The GET endpoint returns the latest persisted diagnostic if available.

The POST endpoint runs diagnostics and persists the latest result.

This can be synchronous because diagnostics must be deterministic and bounded, but it must not perform slow unbounded operations.

If any check is expensive, use timeout/bounded reads and return `unknown` rather than blocking.

## Database

Create:

```text
ticket_diagnostics
```

Suggested fields:

```text
ticket_id
project_id
diagnostic_status
is_stuck
severity
summary
current_state
last_known_step
last_error
checks_json
recommended_actions_json
generated_at
created_at
updated_at
```

Only the latest diagnostic per ticket is required for now.

No historical diagnostic timeline is needed in this ticket.

## Frontend

Add a panel on the ticket detail page:

```text
Ticket Diagnostics
```

Location:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
```

New component suggestion:

```text
apps/dashboard/src/components/TicketDiagnosticsPanel.jsx
```

Display:

- stuck / healthy badge
- severity
- summary
- current state
- last known step
- last error
- checks list
- recommended actions list
- generated date
- button: `Run diagnostics`

Recommended actions should be displayed as suggestions only.

For destructive or future actions, show disabled buttons or badges such as:

```text
Action not wired yet
```

Do not implement destructive actions in this ticket.

## Safety requirements

The diagnostic service must be read-only except for persisting the diagnostic result.

It must not:

- delete files
- delete worktrees
- mutate ticket state
- mutate approvals
- mutate rule evaluations
- run agents
- start/stop daemons
- change Git branches
- push to remote
- merge PRs

## Tests

Add tests for:

- DB persistence of diagnostics
- diagnostic output when ticket is missing
- missing intelligence recommends `rerun_intelligence`
- blocked readiness surfaces blocking reasons
- missing approval recommends `approve_execution` / `reject_execution`
- blocked rules surfaces failed rules
- missing worktree recommends safe recovery action
- merged PR but unfinished ticket recommends `sync_ticket_state`
- API GET/POST diagnostics
- UI rendering of healthy/stuck states and recommended actions
- safety: diagnostic service does not import or call destructive operations

## Acceptance criteria

- A ticket diagnostic can be run from the API.
- The latest diagnostic is persisted in `ticket_diagnostics`.
- The ticket detail page displays a `Ticket Diagnostics` panel.
- Diagnostics include structured checks and recommended actions.
- Diagnostics are bounded and safe to run repeatedly.
- The service is read-only except for persisting diagnostic results.
- No recovery action is executed by this ticket.
- Scheduler, workers, daemon, ticket state machine, Git state, and worktrees are not mutated.
- Existing tests continue to pass.