The plan is written. Here's a summary of what it covers:

---

## Plan T117 — 6 bugs concrets, 6 correctifs localisés

### Analyse des causes racines

| Problème | Cause racine | Fichier(s) |
|---|---|---|
| **Daemon start peu fiable** | `daemon_manager.start()` ne passe ni `--auto-commit`, ni `--auto-push`, ni `--worktrees-dir` → zéro checkpoint automatique | `daemon_manager.py`, `daemon.py` |
| **`_intake` reste sur branche ticket** | `ensure_intake_worktree()` vérifie seulement l'existence du dossier, pas la branche | `worktree_manager.py`, `run_daemon.py` |
| **runtime.log bloque l'intake** | `git checkout HEAD -- path` échoue si le fichier est présent mais non-tracké | `run_issue_intake.py` |
| **Fallback legacy silencieux** | Si le worktree manque et `worktrees_dir` est set, `launch_ticket()` dégrade vers le mode single-repo sans log d'erreur clair | `run_daemon.py` |
| **Friction `--ff-only`** | `_sync_ticket_branch()` refuse les pulls non-fast-forward | `run_daemon.py` |
| **Pas de documentation lifecycle** | Livrable manquant | `docs/daemon-lifecycle.md` (nouveau) |

### Ce que le coder devra faire

**Étape 1** — `daemon_manager.start()` + `daemon.py` : ajouter `--auto-commit`, `--auto-push`, `--worktrees-dir` au Popen du daemon

**Étape 2** — `ensure_intake_worktree()` + `poll_github_issues()` : forcer `git checkout -f main` dans `_intake` à chaque cycle

**Étape 3** — `_cleanup_ignorable_runtime_paths()` : vérifier `git ls-files` avant `git checkout HEAD`

**Étape 4** — `launch_ticket()` : si `worktrees_dir` set + worktree absent → tenter création on-demand, sinon skip (pas de fallback legacy)

**Étape 5** — `_sync_ticket_branch()` : `--rebase` au lieu de `--ff-only`

**Étape 6** — `docs/daemon-lifecycle.md` : documenter le lifecycle complet

### Hors scope
- Docker / deploy
- Suppression du code legacy complet
- Dashboard UI
- Tests automatisés
