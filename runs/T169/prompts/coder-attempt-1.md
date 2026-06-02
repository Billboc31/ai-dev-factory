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


# T169 — T169 - Fix Docker Compose env interpolation ignoring runtime SANDBOX_ID and falling back to default aliases

**Source**: GitHub Issue #190

## Description

# T169 - Fix Docker Compose env interpolation ignoring runtime SANDBOX_ID and falling back to default aliases

## Problem

T168 identified the SANDBOX_ID mismatch between:

- Traefik backend routes
- Docker Compose-generated aliases

However additional debugging now proves the issue is deeper:

```bash
docker compose config | grep sandbox-
```

returns:

```text
sandbox-default-api
sandbox-default-web
```

instead of the expected:

```text
sandbox-main-api
sandbox-main-web
```

This means Docker Compose interpolation itself is not receiving the expected runtime SANDBOX_ID value.

The deploy/runtime flow may export SANDBOX_ID in the shell, but the actual compose interpolation context still falls back to:

```text
${SANDBOX_ID:-default}
```

resulting in broken Traefik routing and DNS resolution.

---

# Root cause hypothesis

One or more of the following is happening:

- `docker compose --env-file deploy/.env` overrides runtime shell env
- compose interpolation occurs before runtime export
- deploy/.env does not contain SANDBOX_ID
- compose subprocess does not inherit shell env correctly
- another compose include/file resets the variable
- runtime worker launches compose with a clean environment

---

# Goal

Make Docker Compose interpolation deterministic and fully driven by the canonical runtime environment id.

Compose config generation itself must produce:

```text
sandbox-main-api
sandbox-main-web
```

before any container starts.

---

# Required fixes

## 1. Generate explicit runtime compose env file

Generate a dedicated runtime env file before compose execution.

Example:

```text
runtime/.env.compose
```

containing:

```env
SANDBOX_ID=main
```

This file becomes the canonical compose interpolation source.

---

## 2. Compose invocation order

Launch compose with deterministic env-file precedence.

Example:

```bash
docker compose \
  --env-file deploy/.env \
  --env-file runtime/.env.compose \
  up -d
```

The runtime env file must override defaults.

---

## 3. Remove reliance on inherited shell env

Do NOT rely on:

```bash
export SANDBOX_ID=...
```

as the primary propagation mechanism.

The worker/deployer/runtime system is too complex and subprocess inheritance is unreliable.

Explicit compose env files must be the source of truth.

---

## 4. Validation before compose up

Before compose startup:

```bash
docker compose config
```

must already contain:

```text
sandbox-main-api
sandbox-main-web
```

If config still resolves to `sandbox-default-*`, fail deployment immediately.

---

## 5. Add runtime diagnostics

Log:

- resolved compose env files
- final SANDBOX_ID value
- `docker compose config` alias snippet
- effective compose project name

This should make future env interpolation issues trivial to diagnose.

---

# Acceptance criteria

- `docker compose config | grep sandbox-` shows sandbox-main aliases for env `main`
- `docker inspect <api>` shows alias `sandbox-main-api`
- Traefik can resolve sandbox-main-api through Docker DNS
- Routed URLs no longer return 502
- No fallback to `sandbox-default-*` occurs unless env id is actually `default`
- Deployments fail early if compose interpolation resolves incorrectly
- Multiple environments continue to work concurrently and deterministically