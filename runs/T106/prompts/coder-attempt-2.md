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


# T106 — T106 — Project issue tree agent and dependency map

**Source**: GitHub Issue #48

## Description

# T106 — Project issue tree agent and dependency map

## Objectif

Créer un agent global projet capable de :

- lire les issues ouvertes
- construire une vue arbre/graphe des tickets
- détecter dépendances et parallélisation possible
- recommander l’ordre d’exécution
- alimenter une nouvelle page dashboard

Sans créer automatiquement de nouveaux tickets.

---

## Vision

Le système doit progressivement évoluer de :

```text
issue queue FIFO
```

vers :

```text
project-aware orchestration
```

---

## Fonctionnement

L’agent :

```text
lit les issues ouvertes
→ analyse les relations
→ construit une map projet
→ détecte :
   - blocked
   - runnable
   - parallelizable
   - depends-on
→ écrit un artefact versionné
```

---

## Dashboard

Ajouter une page :

```text
Project Map
```

avec :

- arbre des tickets
- dépendances
- statut runtime
- tickets bloqués
- tickets parallélisables
- next recommended ticket
- capacité disponible

---

## Agent activity page

Ajouter une vue :

```text
Issue Mapper Activity
```

avec :

- dernier scan
- décisions prises
- reasoning simplifié
- ambiguïtés détectées
- suggestions d’ordre d’exécution

---

## Intégration daemon

Le daemon ne doit plus intake simplement par ordre des issues.

Le daemon doit pouvoir utiliser :

```text
project issue map
```

pour décider :

- quoi lancer
- quoi garder en attente
- quoi paralléliser

---

## Contraintes

- Git reste source de vérité
- pas de DB dédiée
- pas de création automatique d’issues dans cette V1
- garder human gates
- système observable via dashboard et artefacts

---

## Critères d’acceptation

- l’agent produit une map projet exploitable
- le dashboard affiche l’arbre des tickets
- les tickets parallélisables sont détectés
- les tickets bloqués sont identifiés
- le daemon peut utiliser la map pour l’intake/scheduling

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation complete. Here's a summary of what was built:

---

## Files created (6)

| File | Role |
|------|------|
| `tools/agent_runner/run_issue_mapper.py` | Standalone mapper: fetches GitHub issues, parses deps, classifies statuses, detects cycles, writes `.project-map.json` and `.project-map-activity.json` |
| `services/control_api/services/project_map_service.py` | Read-only service + `refresh_project_map()` trigger |
| `services/control_api/routes/project_map.py` | `GET /project-map`, `GET /project-map/activity`, `POST /project-map/refresh` |
| `apps/dashboard/src/api/projectMap.js` | Frontend API client |
| `apps/dashboard/src/pages/ProjectMapPage.jsx` | Project Map page — summary stats, parallelizable groups, blocked tickets, full table |
| `apps/dashboard/src/pages/IssueMapperActivityPage.jsx` | Mapper Activity page — rolling scan history |

## Files modified (4)

| File | Change |
|------|--------|
| `tools/agent_runner/run_daemon.py` | `--poll-project-map` (run mapper each cycle) + `--use-project-map` (next_recommended scheduling with FIFO fallback) |
| `services/control_api/models/schemas.py` | 5 new Pydantic models for project map |
| `services/control_api/main.py` | Registered `project_map` router |
| `apps/dashboard/src/App.jsx` | 2 new nav links + routes |

---

## Review

I have all the information I need. Let me write the review.

---

# PR Review — T106 — Project issue tree agent and dependency map

## Résumé

L'implémentation couvre l'intégralité du scope T106 : agent de mapping, artifacts versionnés, deux pages dashboard, intégration daemon opt-in. La qualité générale du code est bonne : logique correcte, pas de DB, pas de création d'issues automatique, backward-compatible. Un bug concret est identifié sur le path API-triggered refresh.

---

## Vérifications effectuées

- Lecture complète de `run_issue_mapper.py` (631 lignes)
- Lecture du service `project_map_service.py`
- Lecture des routes `project_map.py`
- Lecture des schémas Pydantic ajoutés
- Lecture des pages `ProjectMapPage.jsx` et `IssueMapperActivityPage.jsx`
- Inspection des changements daemon (`run_daemon.py`)
- Lecture de `main.py` (API bootstrap) pour vérifier `app.state`
- Vérification croisée des critères d'acceptation du ticket

---

## Points validés

**Critères d'acceptation du ticket :**

- ✅ L'agent lit les issues ouvertes via `gh issue list` (jusqu'à 500)
- ✅ Construit un graphe de dépendances (parsing `depends on #X`, `blocked by #X`, `requires #X`, `blocks #X`, et format `T###`)
- ✅ Détecte les tickets bloqués (`blocked_dependency`, `blocked_retry`)
- ✅ Détecte les tickets parallélisables (union-find sur tickets immédiatement exécutables)
- ✅ Recommande le prochain ticket (`next_recommended` = lowest-numbered runnable avec deps done)
- ✅ Détecte les cycles (DFS, avec alerte UI)
- ✅ Détecte les ambiguïtés (dépendances vers des issues inexistantes)
- ✅ Écrit deux artifacts atomiques (`.project-map.json` et `.project-map-activity.json`, swap `.tmp`)
- ✅ Page "Project Map" avec summary bar, groupes parallélisables, tickets bloqués, tableau complet
- ✅ Page "Issue Mapper Activity" avec historique des scans (last scan, runnable, blocked, cycles, ambiguités)
- ✅ Intégration daemon via flags opt-in `--poll-project-map` et `--use-project-map` (backward-compatible, FIFO fallback)
- ✅ Aucune création automatique d'issues
- ✅ Pas de DB dédiée — JSON uniquement
- ✅ Human gates préservés
- ✅ Observable via dashboard et artifacts

**Qualité code :**

- La classification deux passes (pass 1 sans deps, pass 2 avec) est correcte et évite les faux blocages par propagation prématurée
- `_atomic_write` avec swap `.tmp` évite les reads partiels
- Schemas Pydantic propres avec defaults raisonnables
- UI réactive avec polling 15s et refresh manuel

---

## Problèmes détectés

### [BLOQUANT] `refresh_project_map` service ne passe pas `--worktrees-dir`

**Localisation :** `services/control_api/services/project_map_service.py:99-108` et `services/control_api/routes/project_map.py:26-30`

Le path API-triggered (`POST /project-map/refresh`) lance le mapper sans `--worktrees-dir` :

```python
# service
cmd = [sys.executable, str(mapper), "--runs-dir", str(_runs_dir(project_root))]
# worktrees_dir ABSENT
```

Or `app.state.worktrees_dir` est déjà configuré dans `main.py:38`. Le mapper sans ce flag ne lit pas les `state.json` dans les worktrees, produisant des statuts erronés pour tous les tickets en worktree mode (tous apparaissent `not_ingested`). Puisque ce projet utilise activement les worktrees, **le bouton "Refresh map" du dashboard produit une map incorrecte**.

De plus, `repo` n'est également pas passé, donc le fetch GitHub est fait sans context de dépôt spécifique.

**Correction à apporter :**

```python
# route: project_map.py
@router.post("/refresh", response_model=ActionResult)
def refresh_project_map(request: Request, background_tasks: BackgroundTasks) -> ActionResult:
    project_root = _root(request)
    worktrees_dir = request.app.state.worktrees_dir  # récupérer depuis app.state
    background_tasks.add_task(
        project_map_service.refresh_project_map,
        project_root,
        worktrees_dir=worktrees_dir,
    )
    return ActionResult(ok=True, message="issue mapper started in background")

# service: project_map_service.py
def refresh_project_map(
    project_root: Path,
    repo: str | None = None,
    worktrees_dir: Path | None = None,
) -> bool:
    cmd = [sys.executable, str(mapper), "--runs-dir", str(_runs_dir(project_root))]
    if repo:
        cmd += ["--repo", repo]
    if worktrees_dir:
        cmd += ["--worktrees-dir", str(worktrees_dir)]
    ...
```

---

### [MINEUR] `T###` dans les regex mappe sur des numéros d'issues, pas des IDs tickets

**Localisation :** `run_issue_mapper.py:47-51`

```python
re.compile(r"(?:depends?\s+on|blocked\s+by|requires?)\s+T(\d+)\b", re.IGNORECASE),
```

Le pattern capture `106` depuis `T106`, mais dans ce projet `T106 → issue #48`. Donc une référence textuelle à `T106` serait interprétée comme une dépendance sur l'issue #106, non sur T106. Résultat : faux positifs dans `ambiguities` et dépendances incorrectes. À documenter ou corriger si des issues body utilisent ce format.

### [MINEUR] Groupes parallélisables toujours en singletons

**Localisation :** `run_issue_mapper.py:293-352`

`compute_parallelizable_groups` filtre les tickets `immediately_runnable` (tous deps done) puis construit les connected components. Mais si tous leurs deps sont done, aucune arête n'existe entre eux dans `has_dep` → chaque ticket forme son propre composant singleton. Le dashboard affiche N groupes de 1 ticket chacun au lieu d'un groupe clair "ces N tickets sont tous parallélisables". C'est fonctionnellement correct mais la sémantique est trompeuse et la valeur affichée limitée.

### [MINEUR] Parsing de dépendances depuis le titre

**Localisation :** `run_issue_mapper.py:453`

```python
text = f"{title}\n{body}"
```

Inclure le titre dans le parsing crée un risque de faux positifs si un titre contient naturellement "depends on" ou "requires" comme description — sans intention de déclarer une dépendance.

---

## Risques éventuels

- **Récursion DFS** dans `detect_cycles` : pour des graphes très profonds (> 1000 tickets), risque de `RecursionError` Python. Pas de souci en pratique avec les volumes actuels.
- **Activity log** borné à 50 entrées : acceptable, intentionnel.
- **Background task bloquante** : `subprocess.run` dans une background task FastAPI bloque le worker thread pendant la durée du scan. Acceptable pour V1 à faible concurrence.

---

## Décision

L'implémentation est structurellement solide et couvre tous les critères d'acceptation du ticket. Un bug concret affecte le refresh dashboard en mode worktrees — c'est le path principal d'utilisation et la correction est triviale (2 fichiers, ~6 lignes).

## Actions demandées

1. **[OBLIGATOIRE]** Passer `worktrees_dir` (depuis `request.app.state.worktrees_dir`) au service `refresh_project_map`, et ajouter `--worktrees-dir` dans la commande subprocess du service.
2. **[RECOMMANDÉ]** Même correction pour `repo` : récupérer depuis `app.state` ou config et le passer au mapper.
3. **[OPTIONNEL]** Revoir la sémantique de `compute_parallelizable_groups` pour retourner un seul groupe de tous les tickets immédiatement parallélisables, plutôt que N singletons.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T106/reviews/implementation-review.md
- generated at: 2026-05-18T06:34:56Z

---

I have all the information I need. Let me write the review.

---

# PR Review — T106 — Project issue tree agent and dependency map

## Résumé

L'implémentation couvre l'intégralité du scope T106 : agent de mapping, artifacts versionnés, deux pages dashboard, intégration daemon opt-in. La qualité générale du code est bonne : logique correcte, pas de DB, pas de création d'issues automatique, backward-compatible. Un bug concret est identifié sur le path API-triggered refresh.

---

## Vérifications effectuées

- Lecture complète de `run_issue_mapper.py` (631 lignes)
- Lecture du service `project_map_service.py`
- Lecture des routes `project_map.py`
- Lecture des schémas Pydantic ajoutés
- Lecture des pages `ProjectMapPage.jsx` et `IssueMapperActivityPage.jsx`
- Inspection des changements daemon (`run_daemon.py`)
- Lecture de `main.py` (API bootstrap) pour vérifier `app.state`
- Vérification croisée des critères d'acceptation du ticket

---

## Points validés

**Critères d'acceptation du ticket :**

- ✅ L'agent lit les issues ouvertes via `gh issue list` (jusqu'à 500)
- ✅ Construit un graphe de dépendances (parsing `depends on #X`, `blocked by #X`, `requires #X`, `blocks #X`, et format `T###`)
- ✅ Détecte les tickets bloqués (`blocked_dependency`, `blocked_retry`)
- ✅ Détecte les tickets parallélisables (union-find sur tickets immédiatement exécutables)
- ✅ Recommande le prochain ticket (`next_recommended` = lowest-numbered runnable avec deps done)
- ✅ Détecte les cycles (DFS, avec alerte UI)
- ✅ Détecte les ambiguïtés (dépendances vers des issues inexistantes)
- ✅ Écrit deux artifacts atomiques (`.project-map.json` et `.project-map-activity.json`, swap `.tmp`)
- ✅ Page "Project Map" avec summary bar, groupes parallélisables, tickets bloqués, tableau complet
- ✅ Page "Issue Mapper Activity" avec historique des scans (last scan, runnable, blocked, cycles, ambiguités)
- ✅ Intégration daemon via flags opt-in `--poll-project-map` et `--use-project-map` (backward-compatible, FIFO fallback)
- ✅ Aucune création automatique d'issues
- ✅ Pas de DB dédiée — JSON uniquement
- ✅ Human gates préservés
- ✅ Observable via dashboard et artifacts

**Qualité code :**

- La classification deux passes (pass 1 sans deps, pass 2 avec) est correcte et évite les faux blocages par propagation prématurée
- `_atomic_write` avec swap `.tmp` évite les reads partiels
- Schemas Pydantic propres avec defaults raisonnables
- UI réactive avec polling 15s et refresh manuel

---

## Problèmes détectés

### [BLOQUANT] `refresh_project_map` service ne passe pas `--worktrees-dir`

**Localisation :** `services/control_api/services/project_map_service.py:99-108` et `services/control_api/routes/project_map.py:26-30`

Le path API-triggered (`POST /project-map/refresh`) lance le mapper sans `--worktrees-dir` :

```python
# service
cmd = [sys.executable, str(mapper), "--runs-dir", str(_runs_dir(project_root))]
# worktrees_dir ABSENT
```

Or `app.state.worktrees_dir` est déjà configuré dans `main.py:38`. Le mapper sans ce flag ne lit pas les `state.json` dans les worktrees, produisant des statuts erronés pour tous les tickets en worktree mode (tous apparaissent `not_ingested`). Puisque ce projet utilise activement les worktrees, **le bouton "Refresh map" du dashboard produit une map incorrecte**.

De plus, `repo` n'est également pas passé, donc le fetch GitHub est fait sans context de dépôt spécifique.

**Correction à apporter :**

```python
# route: project_map.py
@router.post("/refresh", response_model=ActionResult)
def refresh_project_map(request: Request, background_tasks: BackgroundTasks) -> ActionResult:
    project_root = _root(request)
    worktrees_dir = request.app.state.worktrees_dir  # récupérer depuis app.state
    background_tasks.add_task(
        project_map_service.refresh_project_map,
        project_root,
        worktrees_dir=worktrees_dir,
    )
    return ActionResult(ok=True, message="issue mapper started in background")

# service: project_map_service.py
def refresh_project_map(
    project_root: Path,
    repo: str | None = None,
    worktrees_dir: Path | None = None,
) -> bool:
    cmd = [sys.executable, str(mapper), "--runs-dir", str(_runs_dir(project_root))]
    if repo:
        cmd += ["--repo", repo]
    if worktrees_dir:
        cmd += ["--worktrees-dir", str(worktrees_dir)]
    ...
```

---

### [MINEUR] `T###` dans les regex mappe sur des numéros d'issues, pas des IDs tickets

**Localisation :** `run_issue_mapper.py:47-51`

```python
re.compile(r"(?:depends?\s+on|blocked\s+by|requires?)\s+T(\d+)\b", re.IGNORECASE),
```

Le pattern capture `106` depuis `T106`, mais dans ce projet `T106 → issue #48`. Donc une référence textuelle à `T106` serait interprétée comme une dépendance sur l'issue #106, non sur T106. Résultat : faux positifs dans `ambiguities` et dépendances incorrectes. À documenter ou corriger si des issues body utilisent ce format.

### [MINEUR] Groupes parallélisables toujours en singletons

**Localisation :** `run_issue_mapper.py:293-352`

`compute_parallelizable_groups` filtre les tickets `immediately_runnable` (tous deps done) puis construit les connected components. Mais si tous leurs deps sont done, aucune arête n'existe entre eux dans `has_dep` → chaque ticket forme son propre composant singleton. Le dashboard affiche N groupes de 1 ticket chacun au lieu d'un groupe clair "ces N tickets sont tous parallélisables". C'est fonctionnellement correct mais la sémantique est trompeuse et la valeur affichée limitée.

### [MINEUR] Parsing de dépendances depuis le titre

**Localisation :** `run_issue_mapper.py:453`

```python
text = f"{title}\n{body}"
```

Inclure le titre dans le parsing crée un risque de faux positifs si un titre contient naturellement "depends on" ou "requires" comme description — sans intention de déclarer une dépendance.

---

## Risques éventuels

- **Récursion DFS** dans `detect_cycles` : pour des graphes très profonds (> 1000 tickets), risque de `RecursionError` Python. Pas de souci en pratique avec les volumes actuels.
- **Activity log** borné à 50 entrées : acceptable, intentionnel.
- **Background task bloquante** : `subprocess.run` dans une background task FastAPI bloque le worker thread pendant la durée du scan. Acceptable pour V1 à faible concurrence.

---

## Décision

L'implémentation est structurellement solide et couvre tous les critères d'acceptation du ticket. Un bug concret affecte le refresh dashboard en mode worktrees — c'est le path principal d'utilisation et la correction est triviale (2 fichiers, ~6 lignes).

## Actions demandées

1. **[OBLIGATOIRE]** Passer `worktrees_dir` (depuis `request.app.state.worktrees_dir`) au service `refresh_project_map`, et ajouter `--worktrees-dir` dans la commande subprocess du service.
2. **[RECOMMANDÉ]** Même correction pour `repo` : récupérer depuis `app.state` ou config et le passer au mapper.
3. **[OPTIONNEL]** Revoir la sémantique de `compute_parallelizable_groups` pour retourner un seul groupe de tous les tickets immédiatement parallélisables, plutôt que N singletons.

IMPLEMENTATION_FIX_REQUIRED