Tous les tests T113 passent (29/29). Les 4 échecs existants dans `test_daemon_checkpoint.py` sont pré-existants sur `main`.

Voici ma review :

---

## PR Review — T113 : Isolate daemon and intake from developer main repo

## Résumé

L'implémentation crée un worktree permanent `_intake` pour isoler toutes les opérations git du daemon du repo principal développeur. Les 5 étapes du plan sont implémentées, avec des améliorations additionnelles raisonnables (classification des fichiers runtime, clean gate amélioré). Tests : 29/29 passent, aucune régression introduite.

## Vérifications effectuées

- Lecture diff complet de tous les 36 fichiers modifiés
- Lecture des fichiers clés : `worktree_manager.py`, `run_daemon.py`, `runtime_checkpoint.py`, `run_issue_intake.py`, `run_ticket.py`
- Exécution du test suite complet — 29 nouveaux tests + 472 existants
- Vérification des 4 échecs `test_daemon_checkpoint.py` : pré-existants sur `main`, non liés

## Points validés

- **Conformité au ticket** : les 5 exigences du plan sont implémentées — `ensure_intake_worktree`, `call_issue_intake(cwd=)`, `poll_github_issues` avec `_intake`, scan Tier 3, `poll_project_map`/`_load_project_map` pointant vers `_intake/runs/`
- **Backward compatibility** : tous les nouveaux paramètres sont optionnels (`worktrees_dir: Path | None = None`), legacy path préservé
- **Fallback correct** : si `ensure_intake_worktree` échoue → retour sur `git checkout main` dans le repo principal, loggé explicitement
- **Isolation subprocess** : `call_issue_intake(..., cwd=intake_cwd)` route correctement les opérations git de `run_issue_intake.py` vers `_intake`
- **Priorité de scan** : TXXX > main runs > _intake — `seen` dict garantit l'absence de duplication
- **Classification dirty paths** : `is_ignorable_runtime_dirty_path` couvre tous les cas pertinents (`.pyc`, `__pycache__`, logs, project-map, workers, SQLite)
- **Recheck après cleanup** : `check_working_tree_clean` re-valide après `git checkout HEAD --` pour les fichiers ignorables
- **T111 correctement archivé** : `daemon_archived: true` dans `runs/T111/state.json`

## Problèmes détectés

### Observation 1 — `.gitignore` avec blocs dupliqués (cosmétique, non-bloquant)

Le diff ajoute deux fois les mêmes sections (`# Python cache`, `# Runtime generated files`) :

```
# Python cache         ← ajouté une fois
__pycache__/
*.pyc

# Runtime generated files
runs/**/runtime.log
...

# Python cache         ← dupliqué
__pycache__/
*.pyc

# Runtime generated files    ← dupliqué
runs/**/runtime.log
...
```

Aucun impact runtime mais nuit à la lisibilité. À corriger dans un prochain ticket ou avant merge.

### Observation 2 — `poll_project_map` ne voit que `_intake/runs/`, pas les TXXX (gap de précision, non-bloquant)

```python
effective_runs_dir = runs_dir
if worktrees_dir:
    intake_runs = worktrees_dir / "_intake" / "runs"
    if intake_runs.exists():
        effective_runs_dir = intake_runs
```

`run_issue_mapper.py` reçoit uniquement `_intake/runs/`. Si un ticket actif a son état dans un TXXX worktree, le project-map ne reflétera pas son état courant. Impact limité : `scan_tickets` avec ses 3 tiers reste correct pour le scheduling, seul `next_recommended` peut être imprécis. Acceptable comme tradeoff, mais à documenter.

### Observation 3 — `ensure_intake_worktree` : présence de répertoire ≠ worktree valide (robustesse, non-bloquant)

```python
if intake_path.exists():
    return True, intake_path
```

Si le répertoire existe mais n'est pas un worktree git valide (après `git worktree prune` par exemple), `git pull` échouera dans `poll_github_issues` et sera correctement loggé. Le fallback legacy prend le relais. Comportement acceptable mais la vérification pourrait utiliser `git worktree list` pour être plus robuste.

### Observation 4 — `DEBUG dirty working tree:` toujours présent dans `run_ticket.py` (cosmétique)

```python
if real:
    print("DEBUG dirty working tree:")
    print(result.stdout)
    raise TicketRunnerError(...)
```

Le préfixe `DEBUG` est un artifact de développement. Pas de blocage fonctionnel.

### Observation 5 — Dérive de scope vs plan (positive)

Le plan déclarait : *"run_issue_intake.py : aucun changement"*. L'implémentation a modifié `run_issue_intake.py` (clean gate intelligent) et ajouté `runtime_checkpoint.py`. Ce sont des améliorations cohérentes avec l'objectif d'isolation. Pas de dérive problématique, mais le plan était incomplet.

## Risques éventuels

- Si `workers.json` contient de l'état non encore migré vers SQLite, l'auto-restore via `git checkout HEAD -- workers.json` pendant intake pourrait perdre des données daemon. Risque négligeable post-T111.
- La classification par `parse_porcelain_paths` pourrait être incorrecte pour un nom de fichier contenant littéralement ` -> ` — cas pratiquement impossible sur les fichiers surveillés.

## Décision

Les problèmes détectés sont des observations mineures. L'implémentation atteint tous les critères d'acceptation du ticket : isolation complète du daemon, backward compat, fallback, tests couvrant les cas nominaux et d'erreur.

IMPLEMENTATION_APPROVED
