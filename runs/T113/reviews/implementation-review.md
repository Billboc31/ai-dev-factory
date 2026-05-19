Now I have a complete picture of the implementation. Let me write the review.

---

## PR Review — T113 : Isolate daemon and intake from developer main repo

### Résumé

L'implémentation déroute toutes les opérations git du daemon vers un worktree `_intake` dédié. Les 5 étapes du plan sont implémentées. Deux améliorations hors-plan justifiées : la clean gate de `run_ticket.py` et l'extension de `runtime_checkpoint.py`. Les tests couvrent les cas nominaux et d'erreur (476 lignes nouvelles de tests).

---

### Vérifications effectuées

- Lecture de `worktree_manager.py`, `run_daemon.py`, `run_issue_intake.py`, `runtime_checkpoint.py`, `run_ticket.py`, `.gitignore`
- Lecture du diff complet (`git diff main...HEAD --stat` — 41 fichiers)
- Vérification de la conformité plan vs implémentation

---

### Points validés

**Conformité au plan (5/5 étapes)**

| Étape | Statut |
|-------|--------|
| `ensure_intake_worktree()` dans `worktree_manager.py` | ✓ lignes 29-42 |
| `call_issue_intake(cwd=)` | ✓ `cwd` passé à `subprocess.run` |
| `poll_github_issues()` — `git pull` dans `_intake`, plus `git checkout main` dans main repo | ✓ |
| `scan_tickets()` — 3e tier `_intake/runs/*/state.json` | ✓ |
| `poll_project_map()` + `_load_project_map()` → `_intake/runs/` | ✓ |

**Isolation daemon**

Le daemon ne fait plus jamais `git checkout main` dans le repo principal si `_intake` est disponible. Le fallback legacy (checkout main) ne se déclenche que si `ensure_intake_worktree` échoue, et est loggé explicitement. La protection est complète sur le chemin nominal.

**Backward compatibility**

Tous les paramètres nouveaux sont optionnels (`worktrees_dir: Path | None = None`). Sans `--worktrees-dir`, le comportement legacy est identique. Aucune interface publique modifiée.

**Clean gate intelligente — `run_ticket.py`**

La fonction `_check_working_tree_clean()` délègue désormais à `classify_intake_dirty_paths()` pour distinguer les artefacts runtime des vraies modifications. Sans cette amélioration, l'auto-loop serait bloqué par ses propres `.pyc` et `runtime.log`. Scope extension non-planifiée mais indispensable à l'objectif d'isolation.

**`runtime_checkpoint.py` — classification**

`is_ignorable_runtime_dirty_path()` couvre les cas pertinents : `.pyc`, `__pycache__/`, `.sqlite`/WAL/SHM, `runs/*/runtime.log`, `runs/daemon.log`, `runs/workers.json`, `runs/.project-map*.json`. Complet et cohérent avec les patterns `.gitignore`.

**Safety de `checkpoint_transition()`**

- Refuse de committer sur `main` (vérification explicite `rev-parse --abbrev-ref HEAD`)
- `git add -f` borné aux chemins `runs/{ticket_id}/` ou `COMMIT_SCOPE` — pas d'add global
- Vérification `git diff --cached --name-only` avant commit — pas de commit vide
- Post-commit `verify_clean_tree` — garantie d'atomicité perçue

**Création worktrees TXXX**

`create_ticket_worktree()` n'a pas de `cwd` explicite, donc s'exécute depuis le répertoire courant. Acceptable : `git worktree add` n'écrit rien dans le working tree courant, il crée uniquement un nouveau chemin. Pas de pollution du repo principal.

---

### Problèmes détectés

#### Observation 1 — `.gitignore` avec blocs dupliqués (cosmétique, non-bloquant)

Le fichier contient quatre duplications concrètes :

```
# Lignes 24-25 — dupliquent lignes 15-16
__pycache__/
*.pyc

# Lignes 27-30 — dupliquent lignes 20-22 et 58-61
runs/daemon.log
runs/*/runtime.log
runs/runtime.log
runs/daemon.pid

# Lignes 32-44 — trois blocs identiques node_modules//.vite//.pytest_cache/

# Lignes 64-73 — dupliquent exactement lignes 53-62
# Python cache
__pycache__/
*.pyc
# Runtime generated files
runs/**/runtime.log
...
```

Git gère les duplicates silencieusement. Aucun impact runtime. À consolider dans un prochain ticket.

#### Observation 2 — `DEBUG dirty working tree:` toujours présent dans `run_ticket.py` (cosmétique, non-bloquant)

```python
if real:
    print("DEBUG dirty working tree:")
    print(result.stdout)
    raise TicketRunnerError(...)
```

Le préfixe `DEBUG` est un artefact de développement qui s'affichera dans les logs de production. Non-bloquant fonctionnellement mais à nettoyer.

#### Observation 3 — `ensure_intake_worktree` : existence de répertoire ≠ worktree git valide (robustesse, non-bloquant)

```python
if intake_path.exists():
    return True, intake_path
```

Si le répertoire existe sans être un worktree valide (ex: après `git worktree prune`), le `git pull` échouera dans `poll_github_issues` et le fallback legacy prendra le relais — comportement accepté. Une vérification via `git worktree list` serait plus robuste mais n'est pas requise par le ticket.

#### Observation 4 — `poll_project_map` ne voit que `_intake/runs/` (gap de précision, non-bloquant)

Déjà analysé dans la review précédente. Le project-map ne reflète pas l'état courant des tickets en cours dans leurs TXXX worktrees. `scan_tickets` à 3 tiers reste correct pour le scheduling. Tradeoff acceptable.

#### Observation 5 — Dérive de scope positive vs plan

Le plan déclarait : *"run_issue_intake.py : aucun changement"*. L'implémentation a modifié `run_issue_intake.py` (clean gate), étendu `runtime_checkpoint.py`, et modifié `run_ticket.py`. Ces changements sont cohérents avec l'objectif d'isolation et ne constituent pas une dérive problématique. Le plan était incomplet sur ces aspects.

---

### Risques éventuels

- `verify_clean_tree` (dans `checkpoint_transition`) ne filtre pas les runtime paths via `is_ignorable_runtime_dirty_path`. En pratique, les fichiers `.gitignore`d n'apparaissent pas dans `git status --porcelain`, donc risque nul sur le chemin nominal.
- Si `workers.json` contient de l'état non migré vers SQLite, le `git checkout HEAD -- workers.json` lors de l'auto-cleanup intake pourrait écraser des données. Risque résiduel post-T111.

---

### Critères d'acceptation du ticket (vérification)

| Critère | Statut |
|---------|--------|
| repo développeur reste propre | ✓ daemon route via `_intake`, fallback legacy loggé |
| daemon totalement découplé du repo humain | ✓ sur chemin nominal |
| plus aucun blocage intake lié à main dirty | ✓ `check_working_tree_clean` dans `_intake`, plus dans main repo |
| plus aucun checkout automatique dans repo humain | ✓ `git checkout main` supprimé du chemin nominal |

---

### Décision

Les 5 étapes du plan sont correctement implémentées. Les observations sont cosmétiques ou des tradeoffs documentés. Aucun bug bloquant ni violation de sécurité. L'implémentation atteint tous les critères d'acceptation du ticket.

IMPLEMENTATION_APPROVED
