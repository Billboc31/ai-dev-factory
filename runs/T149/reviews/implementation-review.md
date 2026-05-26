---

## Review T149 — Résultat

L'implémentation est **approuvée**. Voici le résumé de la revue.

### Ce qui est validé

**Fix stale lock** — `_sandbox_release_stale_lock` détecte les PID morts avant acquisition, le background thread `_watch_worker` nettoie le PID file dès la fin du worker. Thread-safety correcte via `_sandbox_locks_mutex`.

**Mode branching** — Le flag `keep_environment` dans le `finally` de `_do_sandbox` est propre : validation → teardown complet + port libéré ; environment → compose reste up + port conservé. L'état initial `validating` (vs l'ancien `running`) élimine l'ambiguïté avec les phantom processes.

**State machine** — `validating → validated` (validation), `validating → environment → stopped → cleaned` (environment). Idempotence stop/delete confirmée.

**API et dashboard** — Deux boutons distincts, actions contextuelles Stop/Delete correctes, badge mode visible, désactivation correcte pendant les états actifs.

**Tests** — Les 7 scénarios du ticket sont couverts.

### Observations non-bloquantes

1. **Processus per-sandbox supervisor orphelin en mode environment** : `_do_sandbox_stop` / `sandbox_delete` ne lisent pas `sandbox_dir/runtime/supervisor.pid` et ne tuent pas ce processus. Les services compose sont bien arrêtés par `stop.sh`, mais le mini-superviseur reste en vie. Leak de ressources à surveiller avec usage intensif.

2. **`stop_sandbox_environment` et `delete_sandbox_environment` non testés dans `test_sandbox_runner.py`** — les error paths HTTP (ConnectError, non-ok) ne sont pas couverts au niveau client.

3. **Pas de polling en état `environment`** — un arrêt externe ne se reflète qu'après Refresh manuel.

IMPLEMENTATION_APPROVED
