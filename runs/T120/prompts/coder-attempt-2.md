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


# T120 — T120 dashboard runtime status

**Source**: GitHub Issue #77

## Description

Expose runtime retry information and runtime error details in the dashboard and control API.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 5 changed files are within scope (`runs/T120/runtime.log` is the live log file that was already modified, not something I changed). Implementation is complete.

---

**Summary of changes:**

**Backend — `services/control_api/`**

- `models/schemas.py`: Added `RetryInfo` model (`failure_class`, `retry_count`, `cooldown_until`); extended `TicketSummary` with `retry_info: RetryInfo | None`; extended `TimelineResponse` with `retry_info: RetryInfo | None` and `last_error: str | None`.

- `services/artifact_reader.py`: Added `_read_retry_state(run_dir)` (reads `retry-state.json`, returns `RetryInfo | None`) and `_read_last_error(run_dir)` (scans `runtime.log` in reverse for last `ERROR` line). Updated `get_ticket()` and `get_ticket_timeline()` to call both helpers.

**Frontend — `apps/dashboard/src/`**

- `pages/TicketDetailPage.jsx`: Added `OverviewTab` component rendering a "Retry status" card (`retry_count`, `failure_class`, `cooldown_until`) and a "Last error" card from `TimelineResponse`. The overview tab now fetches from the timeline endpoint. Overview is also included in the polling auto-refresh list alongside `timeline` and `logs`.

- `components/WorkflowTimeline.jsx`: Failed steps annotated with `attempt N — failure_class` when `retry_info` is present on the timeline.

---

## Review

Now I have everything I need to write the review.

---

# PR Review — T120: Dashboard Runtime Status

## Résumé

Implémentation de l'exposition des informations de retry et de la dernière erreur runtime dans l'API de contrôle et le dashboard. Quatre fichiers cibles modifiés correctement. Un fichier hors-scope modifié de manière significative.

## Vérifications effectuées

- Lecture complète du plan (`runs/T120/plan.md`) et comparaison avec l'implémentation
- Lecture de `services/control_api/models/schemas.py`
- Lecture de `services/control_api/services/artifact_reader.py`
- Lecture de `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Lecture de `apps/dashboard/src/components/WorkflowTimeline.jsx`
- `git diff main --name-only` pour identifier tous les fichiers modifiés
- `git diff main -- prompts/generic/planner.md` pour analyser la modification hors-scope

## Points validés

**Backend — schemas.py**
- `RetryInfo` correctement défini (`failure_class: str | None`, `retry_count: int = 0`, `cooldown_until: str | None`) ✓
- `TicketSummary.retry_info: RetryInfo | None` ajouté ✓
- `TimelineResponse.retry_info: RetryInfo | None` et `last_error: str | None` ajoutés ✓
- Rétrocompatibilité maintenue : tous les nouveaux champs sont optionnels ✓

**Backend — artifact_reader.py**
- `_read_retry_state(run_dir)` : lit `retry-state.json`, gère l'absence du fichier, `json.JSONDecodeError`, `OSError`, `ValueError` ✓
- `_read_last_error(run_dir)` : scan inverse de `runtime.log`, retourne le dernier log contenant `"ERROR"` ✓
- `get_ticket()` enrichi avec `retry_info` ✓
- `get_ticket_timeline()` enrichi avec `retry_info` et `last_error` ✓
- `routes/tickets.py` non modifié — correct : l'enrichissement est fait dans artifact_reader.py, les routes retournent déjà les modèles complets ✓
- `list_tickets()` non modifié — correct selon le plan (performance) ✓

**Frontend — TicketDetailPage.jsx**
- `TAB_FETCHERS.overview` pointe vers `api.getTicketTimeline` ✓
- `OverviewTab` affiche `retry_count`, `failure_class`, `cooldown_until` quand `retry_info` est présent ✓
- `OverviewTab` affiche `last_error` en rouge quand présent ✓
- Fallback affiché quand ni retry_info ni last_error ✓
- Tab `overview` inclus dans le polling auto-refresh (ligne 87) ✓

**Frontend — WorkflowTimeline.jsx**
- Annotation rouge sur les steps `failed` quand `retry_info` est présent ✓
- Format `attempt N — failure_class` ou `attempt N` si pas de failure_class ✓

## Problèmes détectés

### [BLOQUANT] — Modification hors-scope : `prompts/generic/planner.md`

Le plan T120 liste exactement 4 fichiers cibles :
- `services/control_api/models/schemas.py`
- `services/control_api/services/artifact_reader.py`
- `apps/dashboard/src/pages/TicketDetailPage.jsx`
- `apps/dashboard/src/components/WorkflowTimeline.jsx`

Or `prompts/generic/planner.md` a été modifié avec +50 lignes de contenu entièrement nouveau : restructuration du prompt planner pour enforcer un format strict de sortie (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`), avec validation et exemple minimal.

Ce changement est :
- absent du plan T120
- absent des critères d'acceptation
- structurellement différent du scope (infrastructure factory, pas dashboard/API)
- potentiellement impactant sur tous les tickets futurs

### [MINEUR] — Annotation de retry sur tous les steps failed

`WorkflowTimeline.jsx` affiche l'annotation retry sur **tous** les steps en état `failed` quand `retry_info` est présent. Comme `retry_info` est un champ de niveau ticket (pas step), cela peut être légèrement trompeur si plusieurs steps sont failed simultanément. En pratique la machine d'état ne produit qu'un seul step failed à la fois — risque négligeable.

### [MINEUR] — Lecture intégrale du log en mémoire

`_read_last_error` charge l'intégralité de `runtime.log` en mémoire avant de scanner en reverse. Pour les runs longues avec de gros logs, cela pourrait être coûteux. Acceptable à l'échelle actuelle.

## Risques éventuels

La modification de `prompts/generic/planner.md` dans cette PR présente un risque indirect : si ce changement introduit une incompatibilité avec le validateur de plan actuel (ou si le validateur n'existe pas encore), tous les tickets futurs pourraient être affectés. Ce changement mérite sa propre revue dans un ticket dédié.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Obligatoire** : Reverter `prompts/generic/planner.md` de cette PR et créer un ticket dédié pour cette amélioration du prompt planner. La modification est valide dans son contenu mais hors du périmètre T120.

2. **Optionnel** : Documenter dans un commentaire ou ticket séparé le comportement de `_read_last_error` par rapport au format exact du log (substring match sur `"ERROR"` case-sensitive) pour faciliter la maintenance future.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T120/reviews/implementation-review.md
- generated at: 2026-05-21T07:37:58Z

---

Now I have everything I need to write the review.

---

# PR Review — T120: Dashboard Runtime Status

## Résumé

Implémentation de l'exposition des informations de retry et de la dernière erreur runtime dans l'API de contrôle et le dashboard. Quatre fichiers cibles modifiés correctement. Un fichier hors-scope modifié de manière significative.

## Vérifications effectuées

- Lecture complète du plan (`runs/T120/plan.md`) et comparaison avec l'implémentation
- Lecture de `services/control_api/models/schemas.py`
- Lecture de `services/control_api/services/artifact_reader.py`
- Lecture de `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Lecture de `apps/dashboard/src/components/WorkflowTimeline.jsx`
- `git diff main --name-only` pour identifier tous les fichiers modifiés
- `git diff main -- prompts/generic/planner.md` pour analyser la modification hors-scope

## Points validés

**Backend — schemas.py**
- `RetryInfo` correctement défini (`failure_class: str | None`, `retry_count: int = 0`, `cooldown_until: str | None`) ✓
- `TicketSummary.retry_info: RetryInfo | None` ajouté ✓
- `TimelineResponse.retry_info: RetryInfo | None` et `last_error: str | None` ajoutés ✓
- Rétrocompatibilité maintenue : tous les nouveaux champs sont optionnels ✓

**Backend — artifact_reader.py**
- `_read_retry_state(run_dir)` : lit `retry-state.json`, gère l'absence du fichier, `json.JSONDecodeError`, `OSError`, `ValueError` ✓
- `_read_last_error(run_dir)` : scan inverse de `runtime.log`, retourne le dernier log contenant `"ERROR"` ✓
- `get_ticket()` enrichi avec `retry_info` ✓
- `get_ticket_timeline()` enrichi avec `retry_info` et `last_error` ✓
- `routes/tickets.py` non modifié — correct : l'enrichissement est fait dans artifact_reader.py, les routes retournent déjà les modèles complets ✓
- `list_tickets()` non modifié — correct selon le plan (performance) ✓

**Frontend — TicketDetailPage.jsx**
- `TAB_FETCHERS.overview` pointe vers `api.getTicketTimeline` ✓
- `OverviewTab` affiche `retry_count`, `failure_class`, `cooldown_until` quand `retry_info` est présent ✓
- `OverviewTab` affiche `last_error` en rouge quand présent ✓
- Fallback affiché quand ni retry_info ni last_error ✓
- Tab `overview` inclus dans le polling auto-refresh (ligne 87) ✓

**Frontend — WorkflowTimeline.jsx**
- Annotation rouge sur les steps `failed` quand `retry_info` est présent ✓
- Format `attempt N — failure_class` ou `attempt N` si pas de failure_class ✓

## Problèmes détectés

### [BLOQUANT] — Modification hors-scope : `prompts/generic/planner.md`

Le plan T120 liste exactement 4 fichiers cibles :
- `services/control_api/models/schemas.py`
- `services/control_api/services/artifact_reader.py`
- `apps/dashboard/src/pages/TicketDetailPage.jsx`
- `apps/dashboard/src/components/WorkflowTimeline.jsx`

Or `prompts/generic/planner.md` a été modifié avec +50 lignes de contenu entièrement nouveau : restructuration du prompt planner pour enforcer un format strict de sortie (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`), avec validation et exemple minimal.

Ce changement est :
- absent du plan T120
- absent des critères d'acceptation
- structurellement différent du scope (infrastructure factory, pas dashboard/API)
- potentiellement impactant sur tous les tickets futurs

### [MINEUR] — Annotation de retry sur tous les steps failed

`WorkflowTimeline.jsx` affiche l'annotation retry sur **tous** les steps en état `failed` quand `retry_info` est présent. Comme `retry_info` est un champ de niveau ticket (pas step), cela peut être légèrement trompeur si plusieurs steps sont failed simultanément. En pratique la machine d'état ne produit qu'un seul step failed à la fois — risque négligeable.

### [MINEUR] — Lecture intégrale du log en mémoire

`_read_last_error` charge l'intégralité de `runtime.log` en mémoire avant de scanner en reverse. Pour les runs longues avec de gros logs, cela pourrait être coûteux. Acceptable à l'échelle actuelle.

## Risques éventuels

La modification de `prompts/generic/planner.md` dans cette PR présente un risque indirect : si ce changement introduit une incompatibilité avec le validateur de plan actuel (ou si le validateur n'existe pas encore), tous les tickets futurs pourraient être affectés. Ce changement mérite sa propre revue dans un ticket dédié.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Obligatoire** : Reverter `prompts/generic/planner.md` de cette PR et créer un ticket dédié pour cette amélioration du prompt planner. La modification est valide dans son contenu mais hors du périmètre T120.

2. **Optionnel** : Documenter dans un commentaire ou ticket séparé le comportement de `_read_last_error` par rapport au format exact du log (substring match sur `"ERROR"` case-sensitive) pour faciliter la maintenance future.

---

IMPLEMENTATION_FIX_REQUIRED