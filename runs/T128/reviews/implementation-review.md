Main branch has 44 pre-existing failures and 557 passing tests. T128 branch has 44 failures and 575 passing tests — meaning T128 added 18 new passing tests and introduced zero regressions.

Now I have all the information needed for the review.

---

# PR Review — T128: Host Supervisor for Daemon and Deployment Jobs

## Résumé

Implémentation d'un superviseur HTTP minimaliste côté hôte (`services/supervisor/main.py`) et d'un chemin de délégation (path 0) dans `daemon_manager.start()/stop()/get_status()`. Le plan approuvé est respecté à la lettre. V1 couvre uniquement le cycle de vie du daemon de coding — pas de registre de jobs génériques.

## Vérifications effectuées

- Lecture complète des fichiers nouveaux et modifiés : `services/supervisor/main.py`, `services/control_api/services/daemon_manager.py`, `services/control_api/models/schemas.py`, `services/control_api/routes/daemon.py`, `deploy/start_supervisor.sh`, `tests/supervisor/test_supervisor.py`, `docker-compose.yml`.
- Exécution des 4 tests superviseur : **4/4 passent**.
- Exécution de la suite complète : 44 échecs — identiques aux 44 pré-existants sur `main`. **Zéro régression introduite par T128.**
- Vérification des critères d'acceptance du ticket un par un.
- Analyse des chemins de délégation, des cas d'erreur, et des comportements implicites.

## Points validés

**Supervisor (`services/supervisor/main.py`)**
- Bind `127.0.0.1:8090` uniquement — pas d'exposition réseau.
- PID file écrit uniquement après `Popen` réussi — exigence explicite du ticket respectée.
- `start_new_session=True` isole correctement le processus daemon.
- `_current_pid()` nettoie le PID file si le processus n'est plus vivant.
- Variables d'environnement (`AI_DEV_FACTORY_PROJECT_ROOT`, `AI_DEV_FACTORY_RUNTIME_ROOT`) respectent les conventions de `runtime_resolver.py`.

**Délégation dans `daemon_manager.py`**
- Path 0 (supervisor) déclenché uniquement si `AI_DEV_FACTORY_SUPERVISOR_URL` est configuré — backward-compatible.
- `ConnectError` et `TimeoutException` retournent `error="supervisor_unreachable"` + `host_command` pour copier-coller — exigence ticket satisfaite.
- Les paths 1, 2, 3 existants sont intacts.
- `get_status()` avec supervisor inaccessible retombe silencieusement sur la vérification locale (comportement sûr documenté).

**Schémas**
- `DaemonStatus.supervisor_available` et `.supervisor_url` optionnels — backward-compatible.
- `ActionResult.error` optionnel — backward-compatible.

**Routes**
- `_enrich_with_supervisor()` appliqué sur `/daemon/status` et `/{project_id}/daemon/status` — cohérent.

**Script de démarrage**
- `set -euo pipefail`, activation venv, export des vars d'env, `exec uvicorn` — propre et opérateur-friendly.

**docker-compose.yml**
- Variable commentée avec explication claire — ne casse rien si laissée commentée.

**Tests**
- Les 4 tests planifiés présents et passants.
- `test_start_delegates_to_supervisor` vérifie l'absence d'appel à `subprocess.Popen` — conforme au critère "no Popen inside Docker when SUPERVISOR_URL is set".

## Problèmes détectés

**Mineurs (non-bloquants)**

1. **`_call_supervisor()` ne capture pas `json.JSONDecodeError`** (`daemon_manager.py:194`): Si le superviseur retourne un body non-JSON (ex. page d'erreur d'un autre service sur le port 8090), l'exception se propage comme 500. Risque très faible en pratique — le superviseur est un service contrôlé — mais rend le code légèrement fragile.

2. **`body: StartRequest = None` avec `# noqa: B008`** (`supervisor/main.py:137`): Contournement non-idiomatique de FastAPI. Le pattern correct serait `Optional[StartRequest] = Body(None)`. Fonctionnellement correct (les tests passent), mais surprenant à la lecture.

3. **`_enrich_with_supervisor()` fait un appel HTTP synchrone sur chaque requête `/daemon/status`** (`routes/daemon.py:27`): Worst-case 2 secondes de latence sur chaque appel de status quand le superviseur est configuré mais inaccessible. Spécifié dans le plan approuvé, acceptable pour une V1. À surveiller si le dashboard est trop lent.

4. **Aucun flag `--issue-repo` dans le spawn superviseur** (`supervisor/main.py:149-158`): La commande `run_daemon.py` spawné par le superviseur ne passe pas `--issue-repo`. Le daemon doit donc hériter cette config via env var ou avoir une valeur par défaut. Comportement identique au path 3 existant — pas une régression T128.

## Risques éventuels

- **Course condition dans `daemon_start()`**: entre le check `_current_pid()` et le `Popen`, un second appel concurrent pourrait démarrer deux daemons. Limitation connue d'un service localhost sans locking — acceptable pour une V1 à usage monoposte.
- **Incohérence potentielle de chemin de log**: Le superviseur utilise `_logs_dir()` et le control API utilise `resolve_logs_dir(project_root)`. Si les env vars `AI_DEV_FACTORY_RUNTIME_ROOT` divergent entre les deux processus, `get_activity()` lira un fichier différent de celui où le superviseur écrit. À documenter dans les instructions de déploiement.

## Décision

L'implémentation respecte fidèlement le plan approuvé. Les critères d'acceptance du ticket sont tous satisfaits. Zéro régression. Les problèmes identifiés sont sous le seuil de blocage pour une V1.

- APPROVED

## Actions demandées

Aucune action bloquante. Améliorations optionnelles post-merge :
- Capturer `json.JSONDecodeError` dans `_call_supervisor()`.
- Documenter la contrainte d'alignement des `AI_DEV_FACTORY_RUNTIME_ROOT` entre superviseur et control API.

IMPLEMENTATION_APPROVED
