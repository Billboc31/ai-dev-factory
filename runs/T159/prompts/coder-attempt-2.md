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


# T159 — T159 - Harden runtime SQLite architecture and degraded-mode recovery

**Source**: GitHub Issue #166

## Description

# T159 - Harden runtime SQLite architecture and degraded-mode recovery

## Problem

The runtime SQLite database regularly becomes corrupted (`database disk image is malformed`) and currently blocks:

- runtime dashboard visibility
- daemon ticket synchronization
- environment visibility
- runtime observability
- ticket execution flow

The current architecture is too fragile because runtime visibility depends too heavily on a single SQLite file.

---

# Goals

- Make the runtime platform resilient to SQLite corruption
- Ensure the Runtime dashboard remains usable even if SQLite fails
- Move toward a single global runtime database architecture
- Reduce corruption probability significantly
- Improve daemon/runtime recovery behavior

---

# Included

## Global runtime database architecture

Move toward:

```text
~/runtime/ai-dev-factory/.runtime/ai-dev-factory.sqlite
```

Rules:

- single runtime DB per ai-dev-factory instance
- worktrees must NOT create their own runtime DBs
- clone-local runtime DBs should be avoided
- runtime state becomes globally indexed

The runtime DB becomes:

- metadata/index/cache layer
- historical/runtime coordination layer

NOT the sole source of truth.

---

## Filesystem-first runtime architecture

The Runtime dashboard and environment visibility must continue functioning without SQLite.

Filesystem runtime state becomes the primary truth source:

```text
runtime/
  sandboxes/
    <sandbox-id>/
      state.json
      validation.json
      logs/
  proxy/routes/
  worktrees/
```

If SQLite fails:

- Runtime UI still renders environments
- sandboxes still appear
- routes still appear
- validation state still appears
- a degraded-mode warning is shown

---

## SQLite degraded-mode fallback

If SQLite access fails:

- log explicit corruption warning
- rename broken DB automatically
- recreate clean DB if possible
- continue runtime in degraded mode
- avoid daemon crash loops

Example:

```text
runtime DB corrupted -> entering degraded mode
```

---

## SQLite startup integrity checks

At startup:

```sql
PRAGMA integrity_check;
```

If integrity check fails:

- quarantine broken DB
- optionally attempt `.recover`
- recreate empty DB if recovery impossible
- continue degraded runtime mode

---

## SQLite hardening pragmas

Enable safer defaults:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;
```

Evaluate additional pragmas if needed.

---

## Single-writer protections

Add protections against multiple daemon writers:

- startup lock file
- daemon singleton guard
- clearer logs when another daemon already exists
- prevent concurrent SQLite writers when possible

---

## Runtime dashboard degraded UX

Runtime UI should display:

```text
SQLite runtime database unavailable
Showing filesystem-derived runtime state
```

The platform should remain observable.

---

## Cleanup of legacy runtime DB locations

Audit and remove accidental DB creation in:

```text
worktrees/*/.runtime/
clones/*/.runtime/
```

Ensure runtime DB path resolution is deterministic and centralized.

---

# Excluded

- No PostgreSQL migration
- No distributed runtime coordination
- No multi-user runtime synchronization
- No HA/replication architecture
- No cloud database support
- No Kubernetes persistence layer

---

# Acceptance criteria

- Runtime dashboard still works if SQLite becomes corrupted
- Daemon does not enter infinite crash/retry loops on malformed DB
- Runtime state remains observable through filesystem fallback
- Only one global runtime DB is used
- Worktrees no longer create runtime SQLite DBs
- SQLite corruption probability is significantly reduced
- Startup integrity checks run automatically
- Broken DBs are quarantined automatically
- Users receive explicit degraded-mode warnings
- Existing deploy/sandbox/runtime flows continue functioning