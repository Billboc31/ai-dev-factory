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


# T214 — Simplify Ticket Workflow by removing Rules as a ticket gate and defer policy enforcement to Dispatcher

**Source**: GitHub Issue #284

## Description

# Simplify Ticket Workflow by removing Rules as a ticket gate and defer policy enforcement to Dispatcher

## Context

Recent work introduced the following workflow timeline:

```text
Intelligence
↓
Readiness
↓
Rules
↓
Human Approval
↓
Ready To Take
↓
Execution
```

During integration testing it became clear that the current `Rules` step duplicates concerns already handled by:

- Ticket Readiness
- Human Approval
- Future Dispatcher
- Workflow engine

Examples of problematic rules:

```text
require_ticket_intelligence
require_readiness_candidate
require_human_approval
block_when_human_review_required
```

These rules create overlapping responsibilities and confusing UI states.

Example:

```text
Readiness = READY_CANDIDATE
Rules = BLOCKED
Human Approval = CURRENT
```

This makes the workflow difficult to understand.

## Goal

Simplify the ticket workflow.

Remove `Rules` as a visible workflow gate and defer policy enforcement to the future Dispatcher.

The ticket workflow should become:

```text
Intelligence
↓
Readiness
↓
Human Approval
↓
Ready To Take
↓
Execution
```

## Scope

### Ticket timeline

Remove the `Rules` step from:

```text
TicketWorkflowTimeline
TicketWorkflowStatus
```

The timeline must no longer display:

```text
Rules BLOCKED
Rules PASSED
```

## Project Rules panel

Temporarily remove or hide the Project Rules panel/UI.

The current rules configuration will be redesigned later as part of the Dispatcher configuration experience.

## Rules engine

Keep the existing code in place if useful, but:

```text
- stop using it as a ticket workflow gate
- stop surfacing rule failures in the ticket timeline
- stop coupling it to Ready To Take computation
```

No business logic migration is required.

## Future direction

Policy evaluation will later be owned by:

```text
Dispatcher Policy Configuration
Dispatcher Eligibility Engine
Dispatcher Scheduler
```

Examples of future dispatcher policies:

```text
require intelligence
require readiness
require human approval
max difficulty
max estimated cost
allowed labels
blocked labels
parallel execution policies
```

## Non-goals

- Do not implement Dispatcher policies in this ticket.
- Do not remove the workflow engine.
- Do not redesign Ready To Take.
- Do not delete Rules code permanently.

## Acceptance criteria

- The ticket workflow timeline no longer contains a Rules step.
- The workflow becomes:
  Intelligence → Readiness → Human Approval → Ready To Take → Execution.
- The Project Rules panel is removed or hidden.
- Rule failures are no longer displayed in ticket pages.
- Existing ticket workflow behavior continues to work.
- Rules code may remain internally but no longer gates ticket progression.
- Existing tests are updated accordingly.
- The UI becomes simpler and easier to understand.