All files parse cleanly. Here's a summary of what was implemented:

---

## Résumé des changements

### Fichiers modifiés (5)

| Fichier | Changement |
|---|---|
| `tools/agent_runner/runtime_db.py` | `get_db_path()` lit `AI_DEV_FACTORY_RUNTIME_ROOT` avant de faire `git rev-parse` |
| `tools/agent_runner/run_daemon.py` | `main()` dérive `runs_dir` et `worktrees_dir` depuis `RUNTIME_ROOT` si défini |
| `services/control_api/services/runtime_resolver.py` | Ajout de `resolve_runs_dir()` et `resolve_worktrees_dir()` respectant `RUNTIME_ROOT` |
| `services/control_api/services/artifact_reader.py` | `_runs_root()` délègue à `resolve_runs_dir()` |
| `services/control_api/main.py` | `create_app()` utilise `resolve_worktrees_dir()` pour le default |

### Nouveaux fichiers (6)

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image multi-stage : `dashboard` (build Vite) → `runtime` (Python + git + Claude CLI) → `web` (nginx) |
| `docker-compose.yml` | 3 services (`daemon`, `api`, `web`) + volume persistant `runtime-data` |
| `.dockerignore` | Exclut `.git`, `__pycache__`, runtime state, `node_modules` |
| `deploy/env.example` | Template — copier vers `deploy/.env` |
| `deploy/bootstrap.sh` | Crée la structure `RUNTIME_ROOT/runs`, `worktrees`, `clones`, etc. |
| `deploy/nginx.conf` | Sert le dashboard SPA + proxifie `/api/` vers le service `api` |

### Logique RUNTIME_ROOT

- Si `AI_DEV_FACTORY_RUNTIME_ROOT=/runtime` est défini :
  - DB SQLite → `/runtime/.runtime/ai-dev-factory.sqlite`
  - `runs_dir` → `/runtime/runs`
  - `worktrees_dir` → `/runtime/worktrees`
- Sans la variable → comportement local inchangé

### Limites connues

1. **Claude CLI auth** : le mount `~/.claude:/root/.claude:ro` dans `docker-compose.yml` suppose une auth déjà faite sur la machine hôte
2. **Git push depuis container** : nécessite le mount `~/.ssh` + `~/.gitconfig` (déjà dans compose)
3. **Dashboard API URL** : le dashboard doit être configuré pour appeler `/api/` (nginx proxy), selon le vite.config existant
