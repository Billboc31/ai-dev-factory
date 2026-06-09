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


# T180 — T180 - Healthcheck failure logs must prioritize actionable Traefik and proxy diagnostics

**Source**: GitHub Issue #212

## Description

## Problem

Environment deploy failures are now mostly caused by `healthcheck.sh`, but the current logs UI does not surface actionable diagnostics first.

Even with the new Full Logs proposal, users would still need to manually inspect a large raw log dump to understand proxy/routing failures.

The most common current failures are related to:

- Traefik routing
- proxy/backend connectivity
- incorrect runtime URLs
- healthcheck endpoint failures
- container/network resolution

---

## Goal

When `failing_step=healthcheck.sh`, the logs UI must prioritize actionable diagnostics before the raw logs.

The raw full logs should still remain available.

---

## Required UI behavior

Add a dedicated "Failure details" section above the raw logs.

When the failing step is `healthcheck.sh`, surface:

- tested URLs
- HTTP status codes
- curl/wget stdout/stderr
- resolved backend URL
- Traefik route diagnostics
- backend container status
- network diagnostics
- validation.json failure_type
- healthcheck exit code

---

## Required backend behavior

Expose structured healthcheck diagnostics from:

- validation.json
- healthcheck stdout/stderr
- runtime proxy diagnostics

Prefer structured fields over raw text parsing when possible.

---

## Important constraint

Do not remove the raw Full Logs view.

The diagnostics section should augment the logs, not replace them.

---

## Acceptance criteria

- Healthcheck failures surface actionable diagnostics immediately
- Traefik/proxy routing issues are visible without opening raw logs
- Tested URLs and HTTP codes are displayed clearly
- validation.json diagnostics are surfaced in the UI
- Raw full logs are still accessible
- Existing step summary behavior remains unchanged

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

65 failures — all pre-existing (confirmed above with `git stash`). No regressions from T180.

---

## Review

IMPLEMENTATION_FIX_REQUIRED

---

## Résumé de la review

L'implémentation backend est solide : parsing `healthcheck.sh` stdout → `healthcheck_diagnostics`, nouvel endpoint `/diagnostics`, wiring complet dans `run_sandbox.py` et `sandbox_runtime_deploy.py`, tests mis à jour sans régression.

**Problème bloquant** : `backend_diagnostics` est fetché par l'API mais silencieusement ignoré dans le frontend. Or c'est précisément là que vivent les informations prioritaires du ticket :

| Champ ticket | Source | Rendu UI actuel |
|---|---|---|
| Traefik route diagnostics | `backend_diagnostics.traefik_probe` | ❌ absent |
| backend container status | `backend_diagnostics.api_container` | ❌ absent |
| resolved backend URL | `backend_diagnostics.backend_urls` | ❌ absent |
| network diagnostics | `backend_diagnostics.traefik_networks` | ❌ absent |
| validation.json `failure_type` | `backend_diagnostics.failure_type` | ❌ absent |

Le plan approuvé mentionnait explicitement "probe table + **backend_diagnostics fields**". Les critères "Traefik/proxy routing issues visible without raw logs" et "validation.json diagnostics surfaced" ne sont pas satisfaits.

**Problème mineur** : aucun test unitaire pour `_parse_healthcheck_output` malgré la logique regex critique.

**Corrections requises** :
1. Dans `LogViewerDrawer`, utiliser `res.data.backend_diagnostics` et le rendre dans la section "Failure details" (failure_type, backend_urls, statut container API, sondes Traefik).
2. Ajouter des tests unitaires minimaux pour `_parse_healthcheck_output`.

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T180/reviews/implementation-review.md
- generated at: 2026-06-09T12:10:10Z

---

IMPLEMENTATION_FIX_REQUIRED

---

## Résumé de la review

L'implémentation backend est solide : parsing `healthcheck.sh` stdout → `healthcheck_diagnostics`, nouvel endpoint `/diagnostics`, wiring complet dans `run_sandbox.py` et `sandbox_runtime_deploy.py`, tests mis à jour sans régression.

**Problème bloquant** : `backend_diagnostics` est fetché par l'API mais silencieusement ignoré dans le frontend. Or c'est précisément là que vivent les informations prioritaires du ticket :

| Champ ticket | Source | Rendu UI actuel |
|---|---|---|
| Traefik route diagnostics | `backend_diagnostics.traefik_probe` | ❌ absent |
| backend container status | `backend_diagnostics.api_container` | ❌ absent |
| resolved backend URL | `backend_diagnostics.backend_urls` | ❌ absent |
| network diagnostics | `backend_diagnostics.traefik_networks` | ❌ absent |
| validation.json `failure_type` | `backend_diagnostics.failure_type` | ❌ absent |

Le plan approuvé mentionnait explicitement "probe table + **backend_diagnostics fields**". Les critères "Traefik/proxy routing issues visible without raw logs" et "validation.json diagnostics surfaced" ne sont pas satisfaits.

**Problème mineur** : aucun test unitaire pour `_parse_healthcheck_output` malgré la logique regex critique.

**Corrections requises** :
1. Dans `LogViewerDrawer`, utiliser `res.data.backend_diagnostics` et le rendre dans la section "Failure details" (failure_type, backend_urls, statut container API, sondes Traefik).
2. Ajouter des tests unitaires minimaux pour `_parse_healthcheck_output`.