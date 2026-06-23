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

# Role — Reviewer

## Mission

Vérifier qu’une implémentation respecte :
- le ticket
- le plan
- les conventions
- l’architecture
- les contraintes sécurité/qualité

## Tu dois

- détecter les dérives de scope
- détecter les violations architecture
- vérifier les impacts potentiels
- vérifier la cohérence mémoire/documentation
- proposer des corrections concrètes

## Tu ne dois pas

- réécrire complètement le code
- introduire un nouveau scope
- accepter des comportements implicites dangereux

## Sortie attendue

Une review structurée conforme à `ai/templates/pr-review-template.md`.

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

# Generic Review Task

Read the ticket below and review the implementation produced for it.

The review must cover:
- correctness relative to the ticket requirements
- scope compliance
- code quality and safety
- blocking issues vs minor observations

The ticket follows.


# T207 — Fix reset_to_planning workflow to correctly restart planning lifecycle

**Source**: GitHub Issue #270

## Description

# Fix reset_to_planning workflow to correctly restart planning lifecycle

## Context

T204 introduced a guarded manual operation:

```text
reset_to_planning
```

A bug has been discovered when this operation is executed.

Current behavior:

```text
reset_to_planning
↓
archives or removes previous planning artifacts
↓
runner enters PLAN_FIX_REQUIRED
↓
auto-run starts planner
↓
runner expects runs/<ticket>/plan.md
↓
ERROR: fix artifact missing
```

Observed runtime log:

```text
auto-run start: state=PLAN_FIX_REQUIRED
auto-run: running step=planner
auto-run: fix artifact missing: runs/T205/plan.md
```

This creates an invalid recovery state.

## Problem

`reset_to_planning` is intended to restart the planning lifecycle from scratch.

However, the current implementation leaves the ticket in a state that assumes a previous plan artifact still exists.

This prevents planner execution and breaks the reset workflow.

## Goal

Ensure that:

```text
reset_to_planning
↓
archives previous planning artifacts
↓
returns ticket to a clean planning lifecycle state
↓
planner executes normally on next run
↓
a new plan.md is generated
```

## Expected behavior

Recommended lifecycle:

```text
reset_to_planning
↓
archive previous planning artifacts
↓
set state = INIT
↓
next auto-run
↓
planner executes normally
↓
runs/<ticket>/plan.md recreated
↓
PLAN_REVIEW_NEEDED
```

## Scope

Investigate:

- Ticket Operations reset logic
- runner state transitions
- planner execution prerequisites
- PLAN_FIX_REQUIRED artifact requirements
- planner validation logic

## Required changes

### Reset operation

Review:

```text
reset_to_planning
```

and ensure it transitions to a state compatible with a full planner restart.

Recommended:

```text
INIT
```

instead of:

```text
PLAN_FIX_REQUIRED
```

when the intent is to regenerate planning artifacts from scratch.

### Planner recovery

Verify that planner execution:

```text
state = INIT
```

never requires an existing:

```text
runs/<ticket>/plan.md
```

### Artifact lifecycle

Ensure:

```text
reset_to_planning
```

may safely archive or remove previous planning artifacts without breaking the next planner execution.

### Similar operations

Audit:

```text
reset_to_coding
```

and confirm that it does not suffer from the same invalid recovery behavior.

## Tests

Add tests covering:

### reset_to_planning

```text
reset_to_planning
↓
archives old artifacts
↓
state becomes INIT
↓
next auto-run executes planner
↓
new plan.md generated
```

### Missing plan artifact

Verify:

```text
state = INIT
```

works correctly when:

```text
runs/<ticket>/plan.md
```

is absent.

### Regression

Ensure:

```text
PLAN_FIX_REQUIRED
```

still behaves correctly when a genuine plan-fix workflow is executed.

## Acceptance criteria

- `reset_to_planning` archives previous planning artifacts.
- The ticket enters a valid restart state.
- Recommended implementation uses `INIT` for full planning restart.
- Next auto-run executes planner successfully.
- Planner regenerates `runs/<ticket>/plan.md`.
- No `fix artifact missing: runs/<ticket>/plan.md` error occurs after reset.
- Existing PLAN_FIX_REQUIRED workflows continue to work.
- `reset_to_coding` has been reviewed for similar issues.
- Existing test suite continues to pass.

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
