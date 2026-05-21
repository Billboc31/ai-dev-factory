---

# PR Review — T131 — Supervisor daemon persistence and unexpected exit handling

## Résumé

L'implémentation couvre l'intégralité du périmètre T131 : détection d'exit inattendu, preservation des métadonnées d'exit, politique de restart, récupération des PID stales, exposition via l'API supervisor, et visibilité dashboard. Six tests superviseur et deux tests dashboard sont ajoutés, couvrant chaque critère d'acceptance.

Les modifications hors-scope visibles dans `git diff main` (analysis_manager, run_analysis, etc.) proviennent du ticket T130 qui précède ce branch — elles ne font pas partie du travail T131.

## Vérifications effectuées

- Lecture complète de `services/supervisor/main.py` : `DaemonState`, `_check_and_maybe_restart()`, `_monitor_daemon()`, lifespan, endpoints `/daemon/status`, `/daemon/start`, `/daemon/stop`
- Lecture de `services/control_api/models/schemas.py` : nouveaux champs `DaemonStatus`, `DaemonStartRequest`
- Lecture de `services/control_api/services/daemon_manager.py` : propagation `restart_policy`, `get_status()` via supervisor, quatre paths de démarrage
- Lecture de `services/control_api/routes/daemon.py` : routes globales et project-scoped
- Lecture de `apps/dashboard/src/pages/DaemonPage.jsx` : `CrashBanner`, badge "Restarting…"
- Lecture de `tests/supervisor/test_supervisor.py` : 10 tests
- Lecture de `apps/dashboard/tests/DaemonPage.test.jsx` : 9 tests dont 2 nouveaux
- Vérification git log pour identifier les commits propres à T131

## Points validés

**Détection d'exit inattendu**
`_monitor_daemon()` tourne en tâche asyncio avec cycle de 5 secondes. `_check_and_maybe_restart()` détecte la mort du process via `_is_alive(pid)` et distingue exit volontaire vs crash grâce au flag `_voluntary_stop` positionné avant le SIGTERM dans `daemon_stop()`. Séquence correcte.

**Métadonnées d'exit**
`last_exit_code` (via `proc.poll()`), `last_exit_time` (ISO 8601 UTC), `last_error` (message descriptif) sont tous correctement stockés dans `DaemonState` et exposés par `GET /daemon/status`. Les 9 champs retournés couvrent l'état complet.

**Politique de restart**
`restart_policy` accepté dans `POST /daemon/start` (supervisor et control-API), persisté dans le PID file JSON, restauré au redémarrage supervisor. `restart-on-crash` incrémente `restart_count` et respawn via `_spawn_daemon()`. La logique de `exit_unexpected = False` après respawn empêche des boucles de restart répétées.

**Détachement du daemon**
`start_new_session=True` présent sur tous les `subprocess.Popen()` du supervisor. Le daemon survit à la fin des requêtes HTTP.

**Récupération PID stale**
Deux points de recovery : lifespan startup et `daemon_status()` — les deux nettoient le PID file si le process est mort. `_remove_pid_file()` is safe (ignore OSError).

**Fix stop/start race**
`_daemon_state.pid = None` et `_daemon_state.started_at = None` effacés immédiatement après `os.kill` dans `daemon_stop()` — test `test_daemon_stop_clears_pid_immediately` le vérifie.

**Fix restauration exec_cmd/restart_policy au redémarrage supervisor**
`_write_pid_file()` persiste les deux champs. `lifespan()` et `daemon_status()` les restaurent depuis le fichier. Test `test_lifespan_restores_exec_cmd_and_restart_policy` le vérifie.

**Dashboard**
`CrashBanner` avec `role="alert"`, affichage conditionnel sur `exit_unexpected`, exit code, timestamp, restart count. Badge "Restarting…" conditionné sur `restart_policy === 'restart-on-crash' && exit_unexpected && !running`.

**Tests**
10 tests superviseur couvrant tous les critères d'acceptance, y compris les deux fixes. 2 tests dashboard (crash banner présent/absent). Tous les tests existants conservés.

## Problèmes détectés

### Observation 1 (mineure) — Thread safety architecturale sans verrou explicite

`_check_and_maybe_restart()` est une fonction synchrone appelée depuis la coroutine event loop, tandis que les route handlers FastAPI (`daemon_stop`, `daemon_start`) tournent dans un thread pool executor. Les globals `_daemon_state`, `_daemon_proc`, `_voluntary_stop` sont partagés entre les deux contextes sans `threading.Lock`.

En pratique, le GIL CPython rend les assignations Python atomiques, et le design du flag `_voluntary_stop` (positionné avant `os.kill`, réinitialisé par le monitor après usage) est correct pour les scénarios réalistes. L'impact d'une race est bénin : dans le pire cas, le monitor détecte le process mort pendant que `daemon_stop()` envoie le SIGTERM, lit `_voluntary_stop = True`, et pose `exit_unexpected = False` — comportement correct.

Ce n'est pas un bug bloquant pour un supervisor localhost single-process, mais c'est une dette technique à noter.

### Observation 2 (mineure) — Badge "Restarting…" sans test dédié

La logique JSX `restart_policy === 'restart-on-crash' && exit_unexpected && !running` n'est pas couverte par un test dashboard spécifique. Le `CrashBanner` est testé, mais pas le badge de status.

### Observation 3 (mineure) — Aucun cap de restart ni backoff

Si le daemon crashe immédiatement à chaque démarrage, le supervisor le respawn indéfiniment toutes les 5 secondes. Ce n'est pas un critère du ticket, c'est une dette identifiée et acceptable pour l'itération courante.

## Risques éventuels

- **Restart storm** : sans backoff/cap, un crash systématique du daemon (mauvaise config, binaire manquant) génère un respawn toutes les 5 secondes. Risque faible en pratique, à adresser dans un ticket dédié.
- **Double appel HTTP supervisor** : `get_status()` appelle `GET /daemon/status` puis `_enrich_with_supervisor()` appelle `GET /health` — deux requêtes HTTP par poll dashboard. Comportement pré-existant (hors scope T131), impact négligeable sur localhost.

## Décision

APPROVED — tous les critères d'acceptance du ticket sont implémentés et testés. Les observations relevées sont mineures et n'affectent pas la correction ni la sécurité de l'implémentation.

## Actions demandées

Aucune action bloquante. En suivi optionnel :
1. Ajouter un test pour le badge "Restarting…" dans `DaemonPage.test.jsx`
2. Ticket suivi pour restart backoff et cap (ex. max 5 tentatives, délai exponentiel)

IMPLEMENTATION_APPROVED
