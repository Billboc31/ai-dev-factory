Le plan est écrit à `runs/T115/plan.md`. Voici un résumé :

---

## Plan T115 — Docker Compose runtime

**Principe directeur** : étendre le hook `RUNTIME_ROOT` (déjà existant comme sentinel bypass dans `run_daemon.py`) à la résolution de tous les chemins runtime. Sans `RUNTIME_ROOT`, le comportement actuel est inchangé.

### Décision importante V1 — Claude reste côté host

Pour T115 V1, **ne pas installer Claude CLI dans l’image Docker**.

Raison : l’objectif prioritaire est de packager le runtime et de stabiliser les chemins, pas de résoudre tout de suite l’authentification Claude dans un container.

Architecture V1 retenue :

```text
Docker Compose
→ control-api
→ dashboard
→ volumes runtime persistants

Host Mac
→ daemon/worker si besoin
→ Claude CLI installé localement
→ Git/SSH déjà configurés
```

Conséquence :

- `EXEC_CMD` reste configurable.
- La documentation doit indiquer que Claude CLI est installé sur l’hôte.
- Le container ne doit pas embarquer de dépendance Claude obligatoire.
- Une intégration Claude-in-container ou host-runner pourra devenir un ticket futur.

### Changements de code (minimes, 3 fichiers)

| Fichier | Changement |
|---|---|
| `tools/agent_runner/runtime_db.py` | `get_db_path()` lit `RUNTIME_ROOT` avant la résolution git |
| `tools/agent_runner/run_daemon.py` | `runs_dir` et `worktrees_dir` dérivés de `RUNTIME_ROOT` si défini |
| `services/control_api/runtime_resolver.py` | idem pour `runs_dir` |

### Nouveaux fichiers (6)

`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/env.example`, `deploy/bootstrap.sh`, `deploy/nginx.conf`

### Risques principaux mis à jour

1. **Boundary host/container** — en V1, Claude CLI et Git/SSH restent côté host ; Docker Compose ne doit pas prétendre exécuter Claude dans le container.
2. **Opérations Git runtime** — les clones/worktrees doivent rester dans `RUNTIME_ROOT`, jamais dans le clone humain.
3. **`runs/TXXX/ticket.md` versionnés vs. volume** — le Coder devra choisir si les `ticket.md` sont copiés du bootstrap image vers le volume, ou régénérés depuis GitHub.
4. **Permissions volumes** — vérifier que les containers peuvent lire/écrire `state/`, `logs/`, `clones/`, `worktrees/` sans casser les permissions host.

### Hypothèses à valider avant codage

1. Docker Compose V1 package au minimum `control-api` + `dashboard` + volumes runtime persistants.
2. Claude CLI n’est pas requis dans l’image Docker V1.
3. Le daemon peut rester lancé côté host dans T115 V1, avec `RUNTIME_ROOT` pointant vers le même runtime root que Compose.
4. Les `ticket.md` versionnés doivent être copiés vers `/runtime/runs/` au bootstrap, ou ignorés si le daemon régénère depuis GitHub.

### Hors scope V1 explicite

- Installer Claude CLI dans Docker.
- Résoudre l’auth Claude dans container.
- Exécuter des agents complets dans un container isolé.
- Docker socket / déploiement Docker-in-Docker.
- Multi-runtime registry complet.
