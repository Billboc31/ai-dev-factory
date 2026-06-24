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


# T211 — Add READY_TO_TAKE eligibility service and unified ticket execution decision

**Source**: GitHub Issue #278

## Description

# Add READY_TO_TAKE eligibility service and unified ticket execution decision

## Context

AI Dev Factory now contains several independent decision systems:

```text
Ticket Intelligence
Ticket Readiness
Execution Rules
Human Approval
```

However, there is currently no single component responsible for answering the most important question:

```text
Can this ticket be taken by a worker?
```

This decision will become the foundation of the future dispatcher and multi-worker scheduler.

## Goal

Introduce a dedicated eligibility service that computes a unified:

```text
READY_TO_TAKE
```

status for every ticket.

The service should explain:

```text
why a ticket can be executed
why a ticket is blocked
what action is required next
```

## Scope

Create a new service:

```text
TicketExecutionEligibilityService
```

that aggregates the existing systems without changing their logic.

The service is read-only.

## Inputs

The service evaluates:

```text
Ticket Intelligence
Ticket Readiness
Rule Evaluation
Human Approval state
Ticket dependencies
Current ticket state
```

## Output

Return a structure similar to:

```json
{
  "ready_to_take": false,
  "status": "BLOCKED",
  "reason": "Human plan approval required",
  "next_action": "Approve plan review",
  "blocking_step": "approval"
}
```

## Example decisions

### Ready

```text
Intelligence completed
Readiness ready_candidate
Rules eligible
Approvals approved
Dependencies satisfied

=> READY_TO_TAKE = true
```

### Blocked by approval

```text
Plan review pending

=> READY_TO_TAKE = false
=> blocking_step = approval
```

### Blocked by dependency

```text
Dependency T001 not merged

=> READY_TO_TAKE = false
=> blocking_step = dependencies
```

## UI

Expose the eligibility result on the Ticket page and integrate it with the workflow timeline introduced in T209.

The UI should clearly display:

```text
READY TO TAKE
BLOCKED
WAITING HUMAN ACTION
DEPENDENCY BLOCKED
```

with the associated reason and next action.

## Non-goals

- No automatic worker assignment.
- No scheduler modifications.
- No dispatcher implementation.
- No automatic ticket start.
- No changes to existing rule engines.

This ticket only centralizes decision making.

## Acceptance criteria

- A dedicated eligibility service exists.
- The service produces a single execution decision for a ticket.
- The service explains why a ticket is blocked.
- The service exposes the next required action.
- Existing Intelligence, Readiness, Rules and Approval logic remain unchanged.
- The workflow timeline displays the eligibility result.
- No scheduler or worker behavior changes are introduced.
- Existing tests continue to pass.