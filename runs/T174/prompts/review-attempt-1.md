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


# T174 — T174 - Redesign environment creation popup with project-context defaults and autocomplete

**Source**: GitHub Issue #200

## Description

# T174 - Redesign environment creation popup with project-context defaults and autocomplete

## Problem

The current environment creation popup asks for project/app root information even when the user is already inside a project context.

This creates confusion and causes frequent deployment/runtime issues:

- wrong repository selected
- wrong project root
- wrong runtime clone
- app not found errors
- deploy started from the wrong cwd/runtime
- duplicate runtime confusion

The current UX is too low-level and exposes implementation details (`project root`) that should not be user-facing.

---

## Goal

Redesign the environment creation popup to be project-context aware.

When creating an environment from inside a project page/context:

- automatically reuse the current project metadata
- remove the manual `project root` field
- provide autocomplete/selectors for branch/environment inputs
- simplify the flow to make environment creation feel lightweight and safe

---

## Required UX behavior

### From a project context

If the user is currently inside a project:

- automatically use the current project/repository
- do NOT ask for project root
- do NOT ask for repository path
- do NOT ask for application root

The popup should focus only on:

- environment name
- branch/ref
- optional runtime settings

---

## Autocomplete requirements

### Branch autocomplete

The branch selector should:

- autocomplete from local + remote git branches
- support typing/filtering
- prioritize:
  - current branch
  - recent branches
  - `ticket/TXXX-*`

### Environment name suggestions

Suggest names such as:

- `main`
- current ticket id
- sanitized branch name
- recent environment names

---

## Runtime/project validation

Before environment creation:

log:

```text
project_id=<resolved project>
repo_url=<resolved repository>
branch=<selected branch>
environment=<env name>
runtime_root=<resolved runtime root>
```

If project metadata cannot be resolved from context:

fail clearly with:

```text
project context missing
```

not:

```text
app not found
```

---

## Important constraints

Do NOT:

- expose filesystem paths in the UI
- ask users for project root manually
- derive repository from current shell cwd
- silently fallback to another repository
- allow runtime/project mismatch

---

## Acceptance criteria

- Creating an environment from a project page does not ask for project root
- Current project metadata is reused automatically
- Branch field supports autocomplete/filtering
- Environment name supports suggestions/autocomplete
- Deploy logs clearly show resolved project/repository/runtime metadata
- Wrong local cwd cannot affect environment creation
- Environment creation flow is simpler and project-centric

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
