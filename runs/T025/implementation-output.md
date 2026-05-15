Implementation complete. Here is a summary:

---

## Changements

### Fichiers modifiés

**`tools/agent_runner/run_daemon.py`** — trois zones modifiées :

1. **Constante** `RETRY_STATE_FILENAME = "retry-state.json"` et dictionnaire `_RETRY_POLICIES` définissant les 7 policies par failure class.

2. **Nouvelles fonctions** (section `retry / cooldown state`) :
   - `_retry_state_path`, `_load_retry_state`, `_save_retry_state`, `_clear_retry_state` — I/O atomique du fichier `retry-state.json`
   - `_read_last_failure_class` — lit la dernière ligne `runtime failure: <class>` dans `runtime.log`
   - `_cooldown_until` — calcule le timestamp ISO d'expiration
   - `_apply_retry_policy` — applique la policy (stop / cooldown / exponential / fixed_delay) et retourne le nouvel état
   - `_is_blocked_by_retry` — retourne True si le ticket est `stopped` ou en cooldown actif

3. **`run_once`** — vérifie `_is_blocked_by_retry` avant d'appeler `launch_ticket`

4. **`launch_ticket`** — après le subprocess : si `rc != 0`, lit la failure class et sauvegarde le retry state ; si `rc == 0`, efface le retry state (reset sur succès)

### Fichiers créés

**`tests/test_daemon_retry_cooldown.py`** — 35 tests couvrant toutes les policies, les fonctions I/O, les checks de blocage, et l'intégration dans `run_once` et `launch_ticket`.

### Policies

| Failure class | Action |
|---|---|
| `quota_exceeded` | cooldown 1h |
| `provider_error`, `process_crashed` | backoff exponentiel 60s×2^n, max 5 retries puis cooldown 1h |
| `process_failed`, `empty_output` | délai fixe 5 min, max 3 retries puis `stopped=true` |
| `write_permission_missing`, `unknown` | `stopped=true` immédiat |

### Vérifications

- 201/201 tests passent, aucune régression
- `run_ticket.py` et `run_step.py` non modifiés
- State file `retry-state.json` écrit atomiquement via rename
