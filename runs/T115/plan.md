Le plan est écrit à `runs/T115/plan.md`. Voici un résumé :

---

## Plan T115 — Docker Compose runtime

**Principe directeur** : étendre le hook `RUNTIME_ROOT` (déjà existant comme sentinel bypass dans `run_daemon.py`) à la résolution de tous les chemins runtime. Sans `RUNTIME_ROOT`, le comportement actuel est inchangé.

### Changements de code (minimes, 3 fichiers)

| Fichier | Changement |
|---|---|
| `tools/agent_runner/runtime_db.py` | `get_db_path()` lit `RUNTIME_ROOT` avant la résolution git |
| `tools/agent_runner/run_daemon.py` | `runs_dir` et `worktrees_dir` dérivés de `RUNTIME_ROOT` si défini |
| `services/control_api/runtime_resolver.py` | idem pour `runs_dir` |

### Nouveaux fichiers (6)

`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/env.example`, `deploy/bootstrap.sh`, `deploy/nginx.conf`

### 3 risques principaux

1. **Claude CLI dans l'image** — installation via script officiel ou binaire ; auth via mount `~/.claude`
2. **Opérations git dans le container** — mount `~/.ssh` + `~/.gitconfig` nécessaires
3. **`runs/TXXX/ticket.md` versionnés vs. volume** — le Coder devra choisir si les ticket.md sont copiés du bootstrap image → volume, ou regénérés depuis GitHub

### 2 hypothèses à valider avant codage

1. Claude CLI est installable proprement dans une image `python:3.11-slim` + `apt git`
2. Les ticket.md versionnés doivent être copiés vers `/runtime/runs/` au bootstrap, ou ignorés (daemon régénère depuis GitHub)
