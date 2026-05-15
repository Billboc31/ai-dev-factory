Le plan est écrit dans `runs/T025/plan.md`. Voici un résumé des décisions clés :

**Architecture** : tout le retry/cooldown est géré exclusivement dans `run_daemon.py`. `run_ticket.py` et `run_step.py` ne sont pas modifiés. La failure class est lue depuis `runtime.log` (déjà écrit par `run_ticket.py` via T018).

**Nouveau fichier de state** : `runs/TXXX/retry-state.json` (daemon-owned), avec `failure_class`, `retry_count`, `cooldown_until`, `stopped`, `stop_reason`.

**Policies** :
- `quota_exceeded` → cooldown 1h
- `provider_error` / `process_crashed` → backoff exponentiel 60s×2^n, max 5 retries puis cooldown 1h
- `process_failed` / `empty_output` → délai fixe 5 min, max 3 retries puis `stopped=true`
- `write_permission_missing` → `stopped=true` immédiat
- `unknown` → `stopped=true` immédiat

**Fichiers à modifier** : uniquement `tools/agent_runner/run_daemon.py` + création `tests/test_daemon_retry_cooldown.py`.
