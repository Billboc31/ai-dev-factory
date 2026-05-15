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


# T102 — T102 — Daemon intake synchronization, queue policy and board view

**Source**: GitHub Issue #43

## Description

# T102 — Daemon intake synchronization, queue policy and board view

## Contexte

Après les premiers runs réels du daemon, plusieurs besoins apparaissent au-delà des bugs corrigés par T101.

T101 traite le hardening immédiat : timeline mapping, ticket id allocation, dirty tree, checkpoint/push avant PR.

Ce ticket T102 cible le comportement d’orchestration global du daemon :

- synchronisation Git avant intake
- éviter d’aspirer toutes les issues `ai-ready`
- politique de queue/concurrence
- visibilité globale dans le dashboard

---

## Problèmes observés / risques

### 1. Intake lancé depuis une branche non-main ou main stale

Le daemon peut être lancé alors que le repo local est sur une branche ticket.

Avant d’ingérer une nouvelle issue GitHub, il faut garantir :

```text
checkout main
pull origin main
then compute ticket id
then create ticket branch
```

Sinon risques :

- ticket id calculé sur un état local stale
- branche créée depuis une mauvaise base
- collisions ou runs incohérents
- dashboard/PR basés sur une branche inattendue

---

### 2. Trop d’issues `ai-ready` peuvent être ingérées d’un coup

Le daemon ne doit pas être un aspirateur à issues.

Si plusieurs issues ont le label `ai-ready`, il faut une politique claire :

```text
max_active_tickets = 1 par défaut
```

Le daemon doit pouvoir décider :

- intake une seule issue
- attendre si un ticket est déjà actif
- ne pas lancer de nouveaux tickets si le système est occupé
- plus tard, autoriser certains tickets parallélisables

---

### 3. Besoin d’une vue board globale

La timeline par ticket est utile, mais il manque une vue globale pour piloter le daemon.

Il faut voir :

```text
Backlog ai-ready
Queued
Running
Waiting human
Retry cooldown
Blocked
PR ready
Done
```

Cette vue doit aider à comprendre :

- ce que le daemon va prendre ensuite
- ce qui est bloqué
- ce qui attend une action humaine
- ce qui est en PR
- pourquoi une issue n’est pas encore lancée

---

## Objectif

Transformer le daemon en orchestrateur contrôlé avec une queue explicite et une visibilité globale.

Le daemon doit rester local-first et Git-native.

---

## Travail demandé

### 1. Synchroniser Git avant intake

Avant tout intake d’une issue GitHub :

```text
assert working tree clean or abort safely
checkout main
pull origin main
then run issue intake
```

Contraintes :

- ne pas écraser de changements locaux
- ne pas checkout main si working tree dirty inconnu
- logs explicites :

```text
syncing main before issue intake
checkout main completed
pull origin main completed
```

---

### 2. Ajouter une politique de queue/concurrence

Ajouter une configuration simple :

```text
max_active_tickets = 1
```

Un ticket est actif si :

- state auto-runnable en cours
- lock présent
- étape running détectée
- PR lifecycle en cours
- retry cooldown actif

À discuter/implémenter prudemment : les tickets en gate humaine peuvent soit bloquer la queue, soit permettre un autre ticket selon une option future.

Pour cette V1 : comportement conservateur recommandé :

```text
si un ticket non terminal existe et n’est pas archivé → ne pas intake une nouvelle issue
```

ou variante :

```text
si uniquement waiting human → intake autorisé seulement si config allow_parallel_waiting_human=true
```

---

### 3. Ne pas intake toutes les issues `ai-ready`

Quand plusieurs issues sont candidates :

- trier par priorité/date
- sélectionner au maximum 1 issue si capacité disponible
- logger les autres comme queued/skipped-for-capacity

Labels futurs possibles :

```text
ai-priority-high
ai-parallelizable
ai-blocked
ai-manual-only
```

Ne pas forcément implémenter tous les labels dans cette V1, mais garder le design extensible.

---

### 4. Ajouter une API board

Ajouter un endpoint :

```text
GET /daemon/board
```

ou :

```text
GET /tickets/board
```

La réponse doit regrouper les tickets/issues par colonnes :

```json
{
  "columns": [
    { "id": "backlog", "label": "Backlog", "items": [] },
    { "id": "queued", "label": "Queued", "items": [] },
    { "id": "running", "label": "Running", "items": [] },
    { "id": "waiting_human", "label": "Waiting human", "items": [] },
    { "id": "blocked", "label": "Blocked", "items": [] },
    { "id": "pr_ready", "label": "PR ready", "items": [] },
    { "id": "done", "label": "Done", "items": [] }
  ]
}
```

La board doit être une projection des artefacts existants, pas une nouvelle source de vérité.

---

### 5. Ajouter une vue dashboard board

Ajouter dans l’IHM une page ou section :

```text
Daemon Board
```

Elle doit afficher :

- backlog issues `ai-ready`
- tickets locaux
- état courant
- gate humaine éventuelle
- retry/cooldown éventuel
- PR si connue
- raison si non lancé

---

## Contraintes

- Ne pas dupliquer la state machine de `run_ticket.py`
- Ne pas créer de DB dédiée pour la queue en V1
- Git reste source de vérité
- Pas de `git add .`
- Pas d’auto-merge
- Le dashboard reste client de la Control API
- Aucun checkout/pull si le working tree contient des changements inconnus

---

## Critères d’acceptation

- le daemon synchronise `main` avant intake d’une nouvelle issue
- le daemon ne lance pas toutes les issues `ai-ready` simultanément
- une limite de capacité existe, au moins `max_active_tickets=1`
- les issues non lancées sont visibles comme queued/skipped-for-capacity
- une API board expose les colonnes principales
- le dashboard affiche une vue board globale
- les logs expliquent pourquoi une issue est lancée ou non
- aucun `git add .`

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All correct. The implementation is complete. Here's a summary:

---

## Changes made

**2 files created:**

- `services/control_api/services/board_service.py` — projects `runs/*/state.json` + `daemon.lock` + `retry-state.json` + `gh issue list` into 7 ordered columns (backlog → queued → running → waiting_human → blocked → pr_ready → done) with strict priority classification
- `apps/dashboard/src/pages/BoardPage.jsx` — kanban board UI with 7 columns, auto-polls every 10s, links ticket IDs to detail pages

**5 files modified:**

- `tools/agent_runner/run_daemon.py` — added `_sync_main_before_intake()` (checks for unknown dirty files, then `git checkout main` + `git pull origin main`), added `_count_active_tickets()`, rewrote `poll_github_issues()` to call sync first, check capacity, sort by issue number, intake at most 1, log others as queued/skipped-for-capacity; added `--max-active-tickets` CLI flag (default: 1)
- `services/control_api/models/schemas.py` — added `BoardItem`, `BoardColumn`, `BoardResponse` models
- `services/control_api/routes/daemon.py` — added `GET /daemon/board` endpoint
- `apps/dashboard/src/api/daemon.js` — added `getBoardData()`
- `apps/dashboard/src/App.jsx` — added `BoardPage` import, `/board` route, and "Board" nav link

---

## Review

I have a complete picture. Writing the review now.

---

# PR Review — T102

## Résumé

L'implémentation couvre les 5 travaux demandés : synchronisation Git avant intake, politique de capacité `max_active_tickets`, sélection de la première issue candidate, endpoint `GET /daemon/board`, et page Board dans le dashboard. Le scope est respecté, aucune DB externe n'a été introduite, pas de `git add .`. Un problème de séquencement dans `poll_github_issues` nécessite une correction avant approbation.

---

## Vérifications effectuées

- Lecture complète de `run_daemon.py`, `board_service.py`, `schemas.py`, `routes/daemon.py`, `BoardPage.jsx`, `api/daemon.js`
- Comparaison avec les 8 critères d'acceptation du ticket
- Vérification des contraintes (pas de DB, Git source de vérité, pas de git add ., pas d'auto-merge)
- Vérification du plan (7 étapes, 7 fichiers)

---

## Points validés

- **Git sync** : `_sync_main_before_intake()` vérifie `git status --porcelain`, classe les fichiers, refuse checkout si fichiers inconnus (safe abort), puis `git checkout main` + `git pull origin main` avec logs explicites ligne par ligne. Contraintes de sécurité respectées.
- **Capacité** : `_count_active_tickets()` compte les tickets non archivés/non fermés. Comparaison `active >= max_active_tickets` correcte. Flag `--max-active-tickets` CLI ajouté avec default 1.
- **Sélection single-issue** : tri par numéro croissant, intake du premier candidat uniquement, les autres loggés `queued` ou `skipped-for-capacity`. Design extensible via le tri.
- **API board** : `GET /daemon/board` retourne 7 colonnes avec classification stricte par priorité (done → pr_ready → waiting_human → blocked → running → queued → backlog). Projection pure, pas de nouvelle source de vérité. Backlog = issues non ingérées via `gh issue list`, failure silencieuse (colonne vide, pas d'erreur 500).
- **UI board** : `BoardPage.jsx` 7 colonnes, code-couleur, polling 10s via `usePolling`, lien ticket_id vers `/tickets/:id`, route `/board` et nav ajoutés dans `App.jsx`.
- **Qualité** : fonctions courtes, nommage explicite, erreurs gérées explicitement, logs utiles, aucune dépendance nouvelle.
- **Scope** : aucune dérive détectée, `run_ticket.py` non modifié, pas de DB.

---

## Problèmes détectés

### [BLOQUANT] `_sync_main_before_intake()` appelée inconditionnellement à chaque cycle de polling

**Fichier** : `tools/agent_runner/run_daemon.py:813`

```python
def poll_github_issues(...):
    if not _sync_main_before_intake():   # ← toujours appelé
        _log("issue intake aborted — git sync failed")
        return
    issues = fetch_ready_issues(label, repo)
    ...
    active = _count_active_tickets(runs_dir)
    if active >= max_active_tickets:
        # log skipped-for-capacity
        return
    # intake
```

La synchronisation Git (`git checkout main` + `git pull origin main`) s'exécute à **chaque cycle de 30 secondes**, même quand :
- toutes les issues sont déjà ingérées (pas de candidats)
- la capacité est pleine (`active >= max_active_tickets`)
- il n'y a aucune issue `ai-ready`

Le ticket spécifie : *"Avant tout intake d'une issue GitHub : checkout main, pull origin main, then run issue intake"*. La synchronisation doit être une précondition de l'intake, pas une précondition de la vérification des issues.

En mode continu, cela provoque un `git checkout main` toutes les 30 secondes en état stable (quand un ticket est en cours de traitement), ce qui est perturbateur pour un développeur travaillant sur une branche ticket et génère des appels réseau (`git pull`) sans utilité.

**Correction** : déplacer `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'intake effectif :

```python
def poll_github_issues(...):
    issues = fetch_ready_issues(label, repo)
    if not issues:
        return
    index = load_issue_index(runs_dir)
    candidates = sorted([i for i in issues if str(i["number"]) not in index], key=lambda i: i["number"])
    already_ingested = [i for i in issues if str(i["number"]) in index]
    for issue in already_ingested:
        _log(f"issue #{issue['number']} already ingested as {index[str(issue['number'])]} — skipping")
    if not candidates:
        _log(f"found {len(issues)} issue(s) with label={label!r} — all already ingested")
        return
    active = _count_active_tickets(runs_dir)
    _log(f"found {len(candidates)} candidate issue(s) active_tickets={active} max_active_tickets={max_active_tickets}")
    if active >= max_active_tickets:
        for issue in candidates:
            _log(f"issue #{issue['number']} ({issue.get('title', '')!r}) skipped-for-capacity active={active} max={max_active_tickets}")
        return
    # Sync main uniquement si on est effectivement sur le point d'intaker
    if not _sync_main_before_intake():
        _log("issue intake aborted — git sync failed")
        return
    issue = candidates[0]
    ...
```

---

### [MINEUR] `BoardItem.title` non renseigné pour les tickets ingérés

**Fichier** : `services/control_api/services/board_service.py:83-88`

Le `title` des tickets n'est pas peuplé dans `BoardItem` — seules les items `backlog` (issues GitHub) ont un titre. Les cartes de tickets affichent `state` ou `branch` en sous-titre (`BoardPage.jsx:34`). Fonctionnel, mais moins lisible. Le titre est disponible dans `runs/{ticket_id}/ticket.md` (première ligne `# ...`) mais pas dans `state.json`. À adresser dans un ticket dédié ou en enrichissant `state.json` lors de l'intake.

---

### [MINEUR] `GET /daemon/board` ne transmet pas `repo` au service

**Fichier** : `services/control_api/routes/daemon.py:40-41`

```python
def daemon_board(request: Request) -> BoardResponse:
    return board_service.get_board(_root(request))
```

`repo` n'est pas passé : `get_board` utilise `repo=None`, donc `gh issue list` s'exécute sans `--repo`. Acceptable en V1 (repo implicite via contexte Git), mais pas extensible si la Control API doit servir plusieurs repos. À documenter ou à corriger si le pattern `request.app.state.repo` est ajouté.

---

## Risques éventuels

- En mode `--once` avec `--poll-issues`, le `_sync_main_before_intake()` inconditionnelle est moins problématique (exécution unique), mais le même problème de séquencement existe.
- Les tickets en `cooldown` (retry-state.json a `cooldown_until` mais pas `stopped=true`) apparaissent en colonne `queued` du board, ce qui peut être trompeur. Comportement accepté par le plan (7 colonnes sans colonne cooldown dédiée).

---

## Décision

Une correction est requise sur le séquencement de `_sync_main_before_intake()` dans `poll_github_issues`. La correction est localisée, à faible risque, et ne nécessite pas de refactoring structurel.

## Actions demandées

1. **[BLOQUANT]** Dans `poll_github_issues` (`run_daemon.py`), déplacer l'appel à `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'appel à `call_issue_intake`. Supprimer le `return` early actuel au début de la fonction.

2. **[OPTIONNEL / V2]** Peupler `BoardItem.title` depuis `runs/{ticket_id}/ticket.md` dans `board_service.py`.

3. **[OPTIONNEL / V2]** Transmettre `repo` depuis `app.state` dans `daemon_board` si un pattern multi-repo est envisagé.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T102/reviews/implementation-review.md
- generated at: 2026-05-15T21:20:46Z

---

I have a complete picture. Writing the review now.

---

# PR Review — T102

## Résumé

L'implémentation couvre les 5 travaux demandés : synchronisation Git avant intake, politique de capacité `max_active_tickets`, sélection de la première issue candidate, endpoint `GET /daemon/board`, et page Board dans le dashboard. Le scope est respecté, aucune DB externe n'a été introduite, pas de `git add .`. Un problème de séquencement dans `poll_github_issues` nécessite une correction avant approbation.

---

## Vérifications effectuées

- Lecture complète de `run_daemon.py`, `board_service.py`, `schemas.py`, `routes/daemon.py`, `BoardPage.jsx`, `api/daemon.js`
- Comparaison avec les 8 critères d'acceptation du ticket
- Vérification des contraintes (pas de DB, Git source de vérité, pas de git add ., pas d'auto-merge)
- Vérification du plan (7 étapes, 7 fichiers)

---

## Points validés

- **Git sync** : `_sync_main_before_intake()` vérifie `git status --porcelain`, classe les fichiers, refuse checkout si fichiers inconnus (safe abort), puis `git checkout main` + `git pull origin main` avec logs explicites ligne par ligne. Contraintes de sécurité respectées.
- **Capacité** : `_count_active_tickets()` compte les tickets non archivés/non fermés. Comparaison `active >= max_active_tickets` correcte. Flag `--max-active-tickets` CLI ajouté avec default 1.
- **Sélection single-issue** : tri par numéro croissant, intake du premier candidat uniquement, les autres loggés `queued` ou `skipped-for-capacity`. Design extensible via le tri.
- **API board** : `GET /daemon/board` retourne 7 colonnes avec classification stricte par priorité (done → pr_ready → waiting_human → blocked → running → queued → backlog). Projection pure, pas de nouvelle source de vérité. Backlog = issues non ingérées via `gh issue list`, failure silencieuse (colonne vide, pas d'erreur 500).
- **UI board** : `BoardPage.jsx` 7 colonnes, code-couleur, polling 10s via `usePolling`, lien ticket_id vers `/tickets/:id`, route `/board` et nav ajoutés dans `App.jsx`.
- **Qualité** : fonctions courtes, nommage explicite, erreurs gérées explicitement, logs utiles, aucune dépendance nouvelle.
- **Scope** : aucune dérive détectée, `run_ticket.py` non modifié, pas de DB.

---

## Problèmes détectés

### [BLOQUANT] `_sync_main_before_intake()` appelée inconditionnellement à chaque cycle de polling

**Fichier** : `tools/agent_runner/run_daemon.py:813`

```python
def poll_github_issues(...):
    if not _sync_main_before_intake():   # ← toujours appelé
        _log("issue intake aborted — git sync failed")
        return
    issues = fetch_ready_issues(label, repo)
    ...
    active = _count_active_tickets(runs_dir)
    if active >= max_active_tickets:
        # log skipped-for-capacity
        return
    # intake
```

La synchronisation Git (`git checkout main` + `git pull origin main`) s'exécute à **chaque cycle de 30 secondes**, même quand :
- toutes les issues sont déjà ingérées (pas de candidats)
- la capacité est pleine (`active >= max_active_tickets`)
- il n'y a aucune issue `ai-ready`

Le ticket spécifie : *"Avant tout intake d'une issue GitHub : checkout main, pull origin main, then run issue intake"*. La synchronisation doit être une précondition de l'intake, pas une précondition de la vérification des issues.

En mode continu, cela provoque un `git checkout main` toutes les 30 secondes en état stable (quand un ticket est en cours de traitement), ce qui est perturbateur pour un développeur travaillant sur une branche ticket et génère des appels réseau (`git pull`) sans utilité.

**Correction** : déplacer `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'intake effectif :

```python
def poll_github_issues(...):
    issues = fetch_ready_issues(label, repo)
    if not issues:
        return
    index = load_issue_index(runs_dir)
    candidates = sorted([i for i in issues if str(i["number"]) not in index], key=lambda i: i["number"])
    already_ingested = [i for i in issues if str(i["number"]) in index]
    for issue in already_ingested:
        _log(f"issue #{issue['number']} already ingested as {index[str(issue['number'])]} — skipping")
    if not candidates:
        _log(f"found {len(issues)} issue(s) with label={label!r} — all already ingested")
        return
    active = _count_active_tickets(runs_dir)
    _log(f"found {len(candidates)} candidate issue(s) active_tickets={active} max_active_tickets={max_active_tickets}")
    if active >= max_active_tickets:
        for issue in candidates:
            _log(f"issue #{issue['number']} ({issue.get('title', '')!r}) skipped-for-capacity active={active} max={max_active_tickets}")
        return
    # Sync main uniquement si on est effectivement sur le point d'intaker
    if not _sync_main_before_intake():
        _log("issue intake aborted — git sync failed")
        return
    issue = candidates[0]
    ...
```

---

### [MINEUR] `BoardItem.title` non renseigné pour les tickets ingérés

**Fichier** : `services/control_api/services/board_service.py:83-88`

Le `title` des tickets n'est pas peuplé dans `BoardItem` — seules les items `backlog` (issues GitHub) ont un titre. Les cartes de tickets affichent `state` ou `branch` en sous-titre (`BoardPage.jsx:34`). Fonctionnel, mais moins lisible. Le titre est disponible dans `runs/{ticket_id}/ticket.md` (première ligne `# ...`) mais pas dans `state.json`. À adresser dans un ticket dédié ou en enrichissant `state.json` lors de l'intake.

---

### [MINEUR] `GET /daemon/board` ne transmet pas `repo` au service

**Fichier** : `services/control_api/routes/daemon.py:40-41`

```python
def daemon_board(request: Request) -> BoardResponse:
    return board_service.get_board(_root(request))
```

`repo` n'est pas passé : `get_board` utilise `repo=None`, donc `gh issue list` s'exécute sans `--repo`. Acceptable en V1 (repo implicite via contexte Git), mais pas extensible si la Control API doit servir plusieurs repos. À documenter ou à corriger si le pattern `request.app.state.repo` est ajouté.

---

## Risques éventuels

- En mode `--once` avec `--poll-issues`, le `_sync_main_before_intake()` inconditionnelle est moins problématique (exécution unique), mais le même problème de séquencement existe.
- Les tickets en `cooldown` (retry-state.json a `cooldown_until` mais pas `stopped=true`) apparaissent en colonne `queued` du board, ce qui peut être trompeur. Comportement accepté par le plan (7 colonnes sans colonne cooldown dédiée).

---

## Décision

Une correction est requise sur le séquencement de `_sync_main_before_intake()` dans `poll_github_issues`. La correction est localisée, à faible risque, et ne nécessite pas de refactoring structurel.

## Actions demandées

1. **[BLOQUANT]** Dans `poll_github_issues` (`run_daemon.py`), déplacer l'appel à `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'appel à `call_issue_intake`. Supprimer le `return` early actuel au début de la fonction.

2. **[OPTIONNEL / V2]** Peupler `BoardItem.title` depuis `runs/{ticket_id}/ticket.md` dans `board_service.py`.

3. **[OPTIONNEL / V2]** Transmettre `repo` depuis `app.state` dans `daemon_board` si un pattern multi-repo est envisagé.

---

IMPLEMENTATION_FIX_REQUIRED