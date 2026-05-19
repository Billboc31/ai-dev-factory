Le plan est écrit à `runs/T113/plan.md`. Voici un résumé :

---

## Plan T113 — Vue d'ensemble

**Scope : 2 fichiers modifiés, 0 fichier recréé**

### Problème racine
Dans `run_daemon.py:1138-1156`, avant chaque intake GitHub, le daemon exécute `git checkout main` puis `git pull origin main` **dans le repo principal développeur**. `run_issue_intake.py` vérifie ensuite le working tree de ce même repo. → Bloque si le développeur a des changements en cours.

### Solution
Créer un worktree permanent `_intake` à `~/ai-dev-factory-worktrees/_intake` sur la branche `main`, et y rediriger toutes les opérations Git du daemon.

### Étapes (dans l'ordre)

| # | Fichier | Changement |
|---|---------|------------|
| 1 | `worktree_manager.py` | Ajouter `ensure_intake_worktree(worktrees_dir)` — crée/vérifie `_intake` |
| 2 | `run_daemon.py` | `call_issue_intake()` — ajouter param `cwd` passé à `subprocess.run` |
| 3 | `run_daemon.py` | `poll_github_issues()` — remplacer `git checkout main` + `git pull` sur main repo par `git pull` dans `_intake`, passer `cwd=_intake` à l'intake |
| 4 | `run_daemon.py` | `scan_tickets()` — ajouter scan de `_intake/runs/*/state.json` comme 3e tier |
| 5 | `run_daemon.py` | `poll_project_map()` + `_load_project_map()` — pointer vers `_intake/runs/` |

**`run_issue_intake.py` : aucun changement** — il utilise déjà des paths relatifs au CWD.

### Invariants préservés
- Fallback legacy si `--worktrees-dir` absent
- Worktrees ticket (TXXX) inchangés
- Aucun changement UX/dashboard
