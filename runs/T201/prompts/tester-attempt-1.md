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


# T201 — T201 - Add Execution Rules Engine and policy-based ticket governance

**Source**: GitHub Issue #258

## Description

# T200 - Add Execution Rules Engine and policy-based ticket governance

## Context

AI Dev Factory now supports:

- Ticket Intelligence
- Ticket Readiness Evaluation
- Human Approval Workflow

The next step is to introduce a configurable Rules Engine.

The Rules Engine decides whether a ticket may progress through the autonomous factory according to project policies.

This component does not execute tickets.

It only evaluates rules and produces decisions.

```text
Ticket
↓
Intelligence
↓
Readiness
↓
Human Approval
↓
Rules Engine
↓
ELIGIBLE / BLOCKED
```

## Goals

Create a generic project-level Rules Engine capable of evaluating execution policies.

Rules must be configurable per project.

The engine must explain every decision.

Example:

```text
ELIGIBLE
All execution rules satisfied.
```

or

```text
BLOCKED
Rule R-004 failed
Human approval required.
```

## Non-goals

Do not:

- start execution automatically
- dispatch workers
- reserve workers
- reorder queues
- implement scheduler changes
- launch daemons

The engine is advisory only.

## Database

Create:

```text
project_execution_rules
```

Suggested fields:

```text
project_id
rule_key
enabled
configuration_json
created_at
updated_at
```

Create:

```text
ticket_rule_evaluation
```

Suggested fields:

```text
ticket_id
project_id
eligibility_status
failed_rules_json
passed_rules_json
warnings_json
evaluated_at
created_at
updated_at
```

## Initial supported rules

### Require readiness candidate

```text
readiness_status == ready_candidate
```

### Require human approval

```text
approval_status == ready_to_take
```

### Require Ticket Intelligence

```text
analysis_status == completed
```

### Maximum estimated AI cost

Example:

```text
max_cost_usd = 0.50
```

Tickets exceeding the limit become blocked.

### Maximum difficulty

Example:

```text
difficulty <= 7
```

### Human review mandatory

Block tickets when:

```text
requires_human_plan_review == true
```

and no approval exists.

## Rules evaluator

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

Responsibilities:

1. Load project rules.
2. Load ticket intelligence.
3. Load readiness state.
4. Load approval state.
5. Evaluate all enabled rules.
6. Persist evaluation.

Suggested output:

```json
{
  "eligibility_status": "blocked",
  "failed_rules": [
    "require_human_approval"
  ],
  "warnings": []
}
```

## API

Add:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

Rule evaluation should run asynchronously and return 202 Accepted.

## Frontend

Add:

```text
Project Rules page
```

Allow enabling/disabling rules and editing thresholds.

Add:

```text
Ticket Rule Evaluation panel
```

Display:

- eligibility status
- failed rules
- warnings
- evaluation date

## Acceptance criteria

- Rules are configurable per project.
- Rule evaluations are persisted.
- Failed rules block eligibility.
- Every decision contains an explanation.
- API exposes rule configuration and evaluations.
- Dashboard displays project rules and ticket evaluations.
- Scheduler and execution pipeline remain unchanged.
- Existing test suite continues to pass.