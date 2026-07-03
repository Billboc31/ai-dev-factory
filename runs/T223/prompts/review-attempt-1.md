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


# T223 — Add project-level option to disable human plan approval gate

**Source**: GitHub Issue #303

## Description

# Context

For production projects, requiring a human to approve the implementation plan before coding starts is an important safety mechanism.

For demos and fully automated showcase projects, however, this approval step slows the pipeline considerably because every ticket waits for manual intervention before implementation.

We need a project-level option allowing demo projects to automatically continue after plan generation while keeping the current behaviour as the default.

# Goal

Add a project runtime setting that enables or disables the Human Plan Approval gate.

Default behaviour must remain unchanged.

# New project setting

```text
PROJECT_REQUIRE_HUMAN_PLAN_APPROVAL
```

Default:

```text
true
```

Demo configuration:

```text
false
```

# Behaviour

## When enabled (default)

Current behaviour:

```text
Plan generated
↓
Waiting for human plan approval
↓
Approve
↓
Implementation
```

## When disabled

```text
Plan generated
↓
Automatically approved
↓
Implementation can continue immediately
```

The system should still persist the generated plan and mark it as auto-approved for auditability.

# Scope

This setting ONLY affects the Human Plan Approval gate.

It must NOT bypass:

- Ticket Intelligence
- Global Dependency Analysis
- Readiness
- Dispatcher scheduling
- Human execution approval (if enabled separately)
- Tests
- CI

# Runtime settings

The option should be configurable:

- per project
- through the existing Global/Project Settings UI
- without requiring a code change
- applied dynamically after configuration reload

# UI

Add a checkbox in Project Settings:

```text
☑ Require Human Plan Approval
```

Help text:

```text
When disabled, implementation plans are automatically approved after generation. Useful for demos and fully automated projects.
```

# Audit

When auto-approved, record clearly:

```text
approval_type = AUTO
approval_reason = PROJECT_SETTING
approved_by = SYSTEM
```

The UI should display that the approval was automatic rather than manual.

# Acceptance criteria

- New project-level runtime setting exists.
- Default value is true.
- Setting can be changed from Project Settings.
- Changing the setting does not require restarting the application.
- When disabled, tickets do not wait for manual plan approval.
- The generated plan is still persisted.
- Automatic approvals are distinguishable from manual approvals in the UI and database.
- All other workflow gates remain unchanged.
- Existing projects continue to behave exactly as before by default.

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
