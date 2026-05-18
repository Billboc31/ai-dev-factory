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
