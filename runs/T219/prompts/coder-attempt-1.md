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


# T219 — Add Backlog Batch dashboard with dependency graph visualization

**Source**: GitHub Issue #294

## Description

# Context

The new batch-based backlog ingestion workflow introduces backlog batches, global dependency analysis, and Dispatcher-driven execution.

As the number of tickets grows, understanding what is currently executing, what is blocked, and what will execute next becomes difficult.

We need a dedicated UI to visualize batches, dependency analysis results, and Dispatcher execution state.

# Goal

Create a new Dispatcher dashboard section dedicated to backlog batches and dependency visualization.

The dashboard should provide a complete view of:

- current executing batch
- next collecting batch
- dependency analysis results
- Dispatcher execution status
- ticket dependency graph

# New page

```text
/dispatcher/batches
```

# MVP Features

## 1. Batch list view

Display all batches in a table.

Columns:

```text
Batch ID
Status
Ticket count
Created at
Last activity
Progress
Current phase
```

Statuses:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

Actions:

```text
Open details
Force freeze
Retry dependency analysis
Recompute dependencies
Cancel batch
```

# 2. Batch detail page

Display detailed information for a selected batch.

Example:

```text
Batch B001
Status: Dispatching

Created: ...
Frozen: ...
Dependency Analysis: Completed
Readiness: Completed
```

Display all tickets with:

```text
Ticket ID
Title
Status
Execution phase
Dependencies
Readiness state
Dispatcher state
```

# 3. Current and next batch overview

Display:

```text
Current batch
Next batch
```

Example:

```text
Current batch: B001 (dispatching)
Next batch: B002 (collecting)
```

This gives operators immediate visibility into upcoming work.

# 4. Dependency graph visualization

Provide a visual graph of ticket dependencies.

Recommended library:

```text
React Flow
```

Each ticket is represented as a node.

Relationships are displayed as edges.

Example:

```text
T001
└── T010
    ├── T011
    ├── T012
    │    └── T016
    └── T013
         └── T015
```

Node colors:

```text
green  = done
blue   = running
gray   = waiting
orange = waiting human
red    = failed
purple = selected by Dispatcher
```

# 5. Execution phase visualization

Provide a phase-oriented view generated from dependency analysis.

Example:

```text
Phase 1
- T001

Phase 2
- T010

Phase 3 (parallel)
- T011
- T012
- T013
```

# 6. Dispatcher insights

Display:

```text
Runnable tickets
Blocked tickets
Blocking reasons
Conflicting tickets
```

Examples:

```text
T015 blocked by T011
T020 conflicts with T021
```

# Refresh behavior

The page should auto-refresh periodically.

Recommended default:

```text
10 seconds
```

# Acceptance criteria

- New `/dispatcher/batches` page exists.
- All batches are visible.
- Operators can inspect current and next batches.
- Dependency graph is rendered visually.
- Dispatcher blocking reasons are visible.
- Execution phases are displayed.
- The page auto-refreshes.
- Graph rendering remains usable with dozens of tickets.
- Existing Dispatcher pages continue to work unchanged.