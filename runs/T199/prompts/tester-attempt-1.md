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

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

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

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

The ticket follows.


# T199 — Add Human Approval Workflow and READY_TO_TAKE lifecycle

**Source**: GitHub Issue #255

## Description

# Add Human Approval Workflow and READY_TO_TAKE lifecycle

## Context

AI Dev Factory now provides:

```text
Ticket Intelligence
↓
Ticket Readiness Evaluation
```

A ticket can now become:

```text
ready_candidate
blocked
```

However, the system still lacks an explicit human approval workflow before a ticket is allowed to enter execution.

We want to introduce a dedicated human validation step.

The objective is to allow humans to decide which tickets may actually be executed by AI agents.

## Goal

Introduce a human approval workflow and a new lifecycle state:

```text
ready_to_take
```

Workflow:

```text
Ticket created
↓
Ticket Intelligence
↓
Ticket Readiness Evaluation
↓
READY_CANDIDATE
↓
Human approval
↓
READY_TO_TAKE
```

Only READY_TO_TAKE tickets will eventually be eligible for automatic execution.

Execution behavior itself is not implemented in this ticket.

## Non-goals

Do not:

- modify scheduler behavior
- automatically start execution
- dispatch workers
- enforce execution rules
- automatically approve tickets
- implement parallel execution

This ticket only introduces the approval workflow.

## Database

Create a new table:

```text
ticket_approvals
```

Suggested columns:

```text
id
project_id
ticket_id
approval_type
approval_status
approved_by
approval_comment
approved_at
created_at
updated_at
```

Canonical statuses:

```text
pending
approved
rejected
```

Approval types:

```text
execution
plan
code
```

For this ticket only `execution` approval is required.

## Ticket lifecycle additions

Introduce new ticket lifecycle state:

```text
ready_to_take
```

Rules:

```text
ready_candidate
+ execution approval approved
→ ready_to_take
```

Otherwise:

```text
ready_candidate
+ no approval
→ remains ready_candidate
```

Rejected approval:

```text
approval_status = rejected
```

must return the ticket to:

```text
blocked
```

with a visible reason.

## Approval service

Create:

```text
tools/agent_runner/ticket_approval_service.py
```

Responsibilities:

- create approval requests
- approve tickets
- reject tickets
- retrieve approval history
- compute effective execution eligibility

Suggested API:

```python
request_execution_approval(...)
approve_execution(...)
reject_execution(...)
get_ticket_approvals(...)
```

## API

Add endpoints:

```text
GET /tickets/{ticket_id}/approvals
POST /tickets/{ticket_id}/approve-execution
POST /tickets/{ticket_id}/reject-execution
```

Approval endpoints should:

- verify ticket currently has `ready_candidate`
- persist approval record
- update effective readiness state

## Frontend

Add a new section on the ticket page:

```text
Human Approval
```

Display:

- approval status
- approval history
- approver
- approval date
- comments

Buttons:

```text
Approve for execution
Reject execution
```

Buttons are enabled only when:

```text
readiness_status == ready_candidate
```

## Board UI

Display clear badges:

```text
READY CANDIDATE
READY TO TAKE
BLOCKED
```

Add filtering by approval state.

## Audit requirements

All approvals and rejections must be persisted.

Nothing should be overwritten.

Approval history must remain visible.

Example:

```text
2026-06-21
Pierre
Approved execution
Comment: Safe backend-only ticket
```

## Acceptance criteria

- Tickets may be approved or rejected for execution.
- Approval history is persisted.
- READY_TO_TAKE lifecycle state exists.
- Only READY_CANDIDATE tickets can be approved.
- Rejected approvals move the ticket back to BLOCKED.
- API exposes approval history.
- Dashboard exposes approval actions and history.
- Scheduler and worker behavior remain unchanged.
- Existing tests continue to pass.