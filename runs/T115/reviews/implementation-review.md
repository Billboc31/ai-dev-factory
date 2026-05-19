Now I have everything I need. Writing the review.

---

## Review — T115 — Package ai-dev-factory as installable Docker Compose runtime

### Périmètre reviewé

Commits `9437ba2` (implémentation initiale) + `0188de4` (correctif post-review-1) sur la branche `ticket/T115-t115-package-ai-dev-factory-as-installable-docker`.

Fichiers examinés : `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/bootstrap.sh`, `deploy/env.example`, `deploy/nginx.conf`, `tools/agent_runner/runtime_db.py`, `tools/agent_runner/run_daemon.py`, `services/control_api/main.py`, `services/control_api/services/artifact_reader.py`, `services/control_api/services/runtime_resolver.py`.

---

### Résumé

Les deux points bloquants relevés en review-1 (`IMPLEMENTATION_FIX_REQUIRED`) ont été corrigés dans le commit `0188de4` :

- Claude CLI retiré du Dockerfile — confirmé (aucun `npm install -g @anthropic-ai/claude-code` dans le stage `runtime`)
- Service `daemon` retiré du `docker-compose.yml` — confirmé (seuls `api` et `web` subsistent)
- Fichiers `.pyc` introduits par T115 (`run_step.cpython-314.pyc`, `runtime_checkpoint.cpython-314.pyc`) désindexés via `git rm --cached` — confirmé par le diff `Bin 25901 -> 0 bytes`

L'architecture V1 plan-approuvée est correctement implémentée.

---

### Points validés

**Architecture V1**

Le Dockerfile multi-stage est propre :
- Stage `dashboard` : build React sur `node:20-slim`, produit `/build/dist`
- Stage `runtime` : `python:3.11-slim` + `git` + `curl`, requirements de la control-api, code source copié, `PYTHONPATH=/app`
- Stage `web` : `nginx:alpine` + artifacts compilés + `deploy/nginx.conf`

Pas de Claude CLI, pas d'orchestrateur, pas de daemon dans l'image. Conforme au plan V1.

**Persistance**

Volume nommé `runtime-data:/runtime` dans docker-compose.yml. Les montages SSH/gitconfig sont en `:ro`. La persistance du runtime state survit au remplacement d'image via le volume nommé indépendant du conteneur.

**Bootstrap idempotent**

`deploy/bootstrap.sh` crée avec `mkdir -p` : `runs/`, `worktrees/`, `clones/`, `logs/`, `state/`, `registry/`, `.runtime/`. Le répertoire `.runtime/` correspond au chemin attendu pour la base SQLite (`/runtime/.runtime/ai-dev-factory.sqlite`), cohérent avec `_DB_FILENAME = ".runtime/ai-dev-factory.sqlite"` dans `runtime_db.py`.

**Résolution RUNTIME_ROOT — cohérente sur les trois composants**

| Composant | Lecture de RUNTIME_ROOT | Résultat |
|---|---|---|
| `runtime_db.py` | `get_db_path()`, ligne 78 | `/runtime/.runtime/ai-dev-factory.sqlite` |
| `run_daemon.py` | `main()`, lignes 1409–1416 | `runs_dir`, `worktrees_dir` dérivés de `RUNTIME_ROOT` |
| `runtime_resolver.py` | `resolve_runs_dir()`, `resolve_worktrees_dir()` | `/runtime/runs`, `/runtime/worktrees` |

Compatibilité ascendante : sans `RUNTIME_ROOT`, tous ces composants replient sur le comportement git-based ou sibling-convention legacy.

**nginx.conf**

SPA routing correct (`try_files $uri $uri/ /index.html`). Proxy `/api/` → `http://api:8080/` — l'URL de résolution DNS inter-service Compose est correcte. Headers reverse-proxy présents (`X-Real-IP`, `X-Forwarded-For`). Timeout `proxy_read_timeout 120s` approprié pour des appels d'orchestration potentiellement longs.

**env.example**

Documente explicitement que le daemon n'est pas conteneurisé en V1. Fournit la commande complète pour le lancer côté host. La section `DAEMON (host-side, V1)` est claire et factuelle.

**.dockerignore**

Exclut correctement : `.runtime/`, `*.sqlite`, `__pycache__/`, `*.py[cod]`, `deploy/.env`, les fichiers de runtime state (`workers.json`, `daemon.pid`, `daemon.log`, `state.json`...). Le build Docker ne fuite pas de données runtime.

---

### Problèmes détectés

**H1 — env_file manquant → échec silencieux au `docker compose up`**

```yaml
env_file: deploy/.env   # pas de required: false
```

Si l'utilisateur n'a pas copié `env.example` → `deploy/.env`, Docker Compose v2 échoue avec `open deploy/.env: no such file or directory` avant même de builder l'image. Le message d'erreur n'oriente pas vers l'action requise. Docker Compose v2.24+ supporte `env_file: [{path: deploy/.env, required: false}]`.

Non bloquant pour l'invariant ticket (le `docker compose up` peut fonctionner dès que l'utilisateur copie le fichier), mais c'est un point d'échec UX évident lors de l'installation.

**M1 — resolve_ticket_cwd() lit workers.json depuis project_root/runs (hardcodé)**

Dans `runtime_resolver.py`, ligne 76 :

```python
def resolve_ticket_cwd(ticket_id, project_root, worktrees_dir=None):
    runs_dir = project_root / "runs"  # n'utilise pas RUNTIME_ROOT
    workers = _load_workers(runs_dir)
```

Alors que `resolve_runs_dir()` existe et fait la résolution correcte. Si l'API tente un jour d'exécuter `run_ticket.py` depuis le container (via `subprocess_runner.py`) avec `RUNTIME_ROOT=/runtime`, la résolution du worktree actif échouera car `workers.json` est dans `/runtime/runs/workers.json` et non dans `project_root/runs/`.

En V1 ce chemin de code n'est pas déclenché (Claude CLI absent du container = pas d'exécution de ticket depuis l'API). C'est un bug latent à corriger en V2.

**m1 — Commentaire stage runtime inexact**

`Dockerfile`, ligne 9 : `# Stage 2: Runtime base image (daemon + control-api)`. Le daemon n'est plus dans le container depuis la correction. Le commentaire reste une trace de l'ancienne intention.

**m2 — 51 fichiers .pyc pré-existants trackés sur main**

`git ls-tree -r --name-only main | grep "\.pyc"` retourne 53 entrées — ces fichiers existaient sur main avant T115. T115 a introduit 2 nouveaux `.pyc` puis les a correctement retirés. Les 51 restants sont de la dette pré-existante, hors scope T115, mais la condition "aucun pycache versionné" du ticket n'est pas globalement respectée dans le repository. À adresser dans un ticket dédié.

---

### Risques éventuels

**R1 — Daemon / volume : path resolution côté host**

`env.example` indique : `RUNTIME_ROOT=<host path of the runtime-data volume>`. Pour un volume nommé Docker, le path host est `/var/lib/docker/volumes/<stack>_runtime-data/_data` — non trivial à découvrir. Si le daemon pointe vers un chemin différent, la base SQLite est splitée (daemon écrit dans un endroit, l'API lit dans un autre). Ce risque opérationnel doit être documenté : `docker volume inspect <stack>_runtime-data --format '{{.Mountpoint}}'` donne le path exact.

**R2 — Pas de healthcheck sur le service api**

`restart: unless-stopped` sans `healthcheck` peut conduire à ce que le service `web` démarre avant que l'API soit prête (`depends_on: api` sans condition de santé). Conséquence : requêtes `/api/` en échec pendant le démarrage. Non bloquant en usage normal, mais observable lors de redémarrages à chaud.

---

### Vérifications ticket (invariants)

| Invariant | État |
|---|---|
| produit installé ≠ repo source | ✅ Volume nommé isolé du code source |
| runtime data persistante | ✅ Volume nommé survive au replace d'image |
| runtime redémarrable | ✅ `restart: unless-stopped` + volume |
| runtime remplaçable | ✅ Volume indépendant de l'image |
| plusieurs runtimes possibles | ✅ Chaque instance Compose a son `runtime-data` |
| plusieurs projets gérés possibles | ✅ RUNTIME_ROOT configurable par instance |
| worktrees runtime isolés | ✅ `/runtime/worktrees/` sur volume |
| aucun runtime state versionné | ✅ .gitignore + .dockerignore |
| aucun log versionné | ✅ .gitignore exclut daemon.log, runtime.log |
| aucun pycache versionné (T115) | ✅ Les 2 .pyc introduits par T115 ont été retirés |
| aucun pycache versionné (global) | ⚠️ 51 fichiers pré-existants sur main, hors scope T115 |
| aucun checkout dans clone humain | ✅ Aucune modification des clones humains |

---

### Décision

Les deux points bloquants de la review précédente sont correctement corrigés. L'architecture V1 est implémentée conformément au plan approuvé. Le risque opérationnel sur la découverte du path du volume (R1) et le bug latent sur `resolve_ticket_cwd` (M1) sont documentés pour les tickets suivants.

IMPLEMENTATION_APPROVED
