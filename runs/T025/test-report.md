# Test Report — T025 — Daemon retry and cooldown policy

## Commandes exécutées

```
python -m pytest tests/test_daemon_retry_cooldown.py -v
python -m pytest --tb=short -q
```

## Résultats

```
tests/test_daemon_retry_cooldown.py: 35 passed in 0.03s
Full suite: 201 passed in 0.16s
```

---

## Critères d'acceptation

### 1. Un quota exceeded ne boucle pas infiniment

**PASS**

- Policy `quota_exceeded` → `cooldown_until` = now+3600s, pas de `stopped=True`.
- `_is_blocked_by_retry` retourne `True` tant que le cooldown est actif → `launch_ticket` non appelé.
- Tests couvrant : `test_apply_retry_policy_quota_exceeded_sets_cooldown`, `test_apply_retry_policy_quota_exceeded_cooldown_roughly_one_hour`, `test_run_once_skips_ticket_in_cooldown`.
- Code vérifié : `run_daemon.py:43-51` (policy dict), `run_daemon.py:172-176` (application), `run_daemon.py:395-408` (check dans `run_once`).

### 2. Les retries sont limités et traçables

**PASS**

- `provider_error` / `process_crashed` : max 5 retries, puis fallback cooldown 1h. Après le cooldown, le cycle peut reprendre mais ne boucle jamais sans délai.
- `process_failed` / `empty_output` : max 3 retries, puis `stopped=True` — arrêt définitif.
- `write_permission_missing` / `unknown` : `stopped=True` immédiat.
- `retry_count` incrémenté et persisté dans `retry-state.json` à chaque tentative.
- Tests couvrant toutes les transitions : `test_apply_retry_policy_provider_error_*`, `test_apply_retry_policy_process_failed_after_max_retries_stops`.

### 3. Les cooldowns sont persistés

**PASS**

- `retry-state.json` écrit atomiquement via `.tmp` + `.replace()` (POSIX rename) dans `runs/{ticket_id}/retry-state.json`.
- Rechargé à chaque cycle de `run_once` via `_load_retry_state`.
- Reset sur succès via `_clear_retry_state`.
- Tests : `test_save_and_load_retry_state_round_trip`, `test_clear_retry_state_removes_file`, `test_launch_ticket_saves_retry_state_on_failure`, `test_launch_ticket_clears_retry_state_on_success`.

### 4. Les logs daemon sont explicites

**PASS**

- Chaque décision de policy produit un log structuré avec ticket_id, failure_class, action, délai, reason.
- Exemples de messages vérifiés en test :
  - `"cooldown"` + `"T001"` → `test_is_blocked_by_retry_logs_remaining_seconds_when_in_cooldown`
  - `"human attention"` → `test_is_blocked_by_retry_logs_human_attention_when_stopped`
- Format : `[ISO_TS] [daemon] {ticket_id}: retry policy={action} failure={class} ...`

### 5. Les tests couvrent les policies principales

**PASS**

- 35 tests dédiés dans `tests/test_daemon_retry_cooldown.py`.
- Couverture : I/O state (4 tests), lecture failure class (4 tests), stop policies (3), cooldown policy (2), exponential policy (4), fixed_delay policy (3), `_is_blocked_by_retry` (6), `run_once` integration (4), `launch_ticket` integration (5).
- Toutes les 7 failure classes sont couvertes.

### 6. Le workflow existant reste compatible

**PASS**

- `run_ticket.py` et `run_step.py` non modifiés (confirmé par `git diff main...HEAD`).
- `state.json` (workflow state) non touché par le retry system — `retry-state.json` est un fichier séparé daemon-owned.
- Suite complète : **201/201 tests passent**, zéro régression.
- `AUTO_RUNNABLE_STATES` et `HUMAN_GATE_STATES` inchangés.

---

## Régressions observées

Aucune. 201/201 tests passent dont les suites pré-existantes (`test_daemon_issue_polling.py` et les autres).

## Problèmes bloquants

Aucun.

## Limites de validation

- La persistance du cooldown entre redémarrages du daemon n'est pas testée au niveau système (redémarrage du process) mais est garantie par l'écriture fichier avant tout retry.
- Le comportement de `_read_last_failure_class` sur un log accumulant plusieurs runs n'est pas testé en isolation complète, mais la logique lit bien la **dernière** occurrence (correct pour le cas nominal).
- Aucun test de charge ou de concurrence multi-tickets (hors scope T025).

---

## Décision

**TEST_COMPLETE — PASS**

Les 6 critères d'acceptation sont validés. 35 tests dédiés passent. Zéro régression sur la suite complète (201 tests).
