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


# T195 — T195 - Correct bootstrap onboarding to use standard ai/docs/prompts/runs/tickets layout

**Source**: GitHub Issue #242

## Description

# Objective

T194 was initially picked up with the wrong specification.

The implementation must not create a new generic onboarding format such as:

```text
.ai-dev-factory/
```

Instead, project bootstrap must install the same standard AI Dev Factory layout already used by the `ai-dev-factory` project itself.

This ticket supersedes the wrong T194 interpretation.

---

# Required correction

Bootstrap must generate and propose the standard project-local agent workspace:

```text
ai/
docs/
prompts/
runs/
tickets/
```

Do not invent a new folder name.
Do not create `.ai-dev-factory/`.
Do not implement a vague suggestion/onboarding system.

We already know the expected structure because it exists in `ai-dev-factory`.

---

# Source of truth

Use the existing working `ai-dev-factory` repository layout as the reference implementation.

The bootstrap logic should copy/adapt the known agent folders and files from AI Dev Factory conventions into the managed project.

Expected top-level folders:

```text
ai/
docs/
prompts/
runs/
tickets/
```

The generated contents should be project-specific where needed, but the shape must match the known working layout.

---

# Required behavior

When importing/bootstraping a managed project, the system must:

1. Register/validate the project.
2. Create/resolve the project runtime root.
3. Create a setup branch in the target repository, for example:

```text
ai-dev-factory/bootstrap-agent-layout
```

4. Generate the standard folders:

```text
ai/
docs/
prompts/
runs/
tickets/
```

5. Fill project-specific values such as:

- project id
- project name
- repo URL
- default branch
- validation commands
- runtime/project paths when needed

6. Commit the generated files on the setup branch.
7. Open a PR on the target project proposing those changes.

Bootstrap must never commit directly to the target default branch.

---

# Agent integration

The agent runner must load project-local context from the standard folders:

```text
<project_root>/ai/
<project_root>/docs/
<project_root>/prompts/
<project_root>/runs/
<project_root>/tickets/
```

At minimum:

- run-ticket uses `tickets/` and `runs/` project context
- planner uses `prompts/` and `docs/`
- implementation uses `prompts/`, `docs/`, and project conventions
- review uses `prompts/` and safety/conventions docs
- test/validation uses project docs/prompts and detected validation commands

Existing projects without this layout should keep working with defaults, but bootstrapped projects must prefer project-local context.

---

# Cleanup of wrong T194 direction

If any code from the earlier T194 interpretation exists, remove or correct it:

- no `.ai-dev-factory/` generated folder
- no generic `agent-context.md`-only onboarding model
- no vague optional file suggestions
- no new format detached from the existing AI Dev Factory layout

---

# PR behavior

The setup PR in the target project should be titled something like:

```text
Add AI Dev Factory agent workspace
```

The PR body must explain:

- that it installs the standard AI Dev Factory agent layout
- which folders were added
- how agents use `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/`
- detected validation commands
- any TODOs that require human review

If PR creation fails:

- keep the local branch/commit when possible
- expose the failure in bootstrap result and UI
- do not fail project registration unless strict mode is requested

---

# Acceptance criteria

- T194 wrong `.ai-dev-factory/` direction is not implemented.
- Bootstrap creates `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/` in the target project.
- The generated layout follows the existing `ai-dev-factory` project conventions.
- Bootstrap commits the generated layout on a setup branch.
- Bootstrap opens a PR when a GitHub remote is available.
- Agent runner steps load project-local context from these folders when present.
- Existing projects without the layout keep working with defaults.
- UI shows the bootstrap agent-layout status and PR URL if created.

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
