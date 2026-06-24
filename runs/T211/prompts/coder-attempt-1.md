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