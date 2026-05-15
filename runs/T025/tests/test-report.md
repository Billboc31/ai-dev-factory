---

## Test Report — T025 — Daemon retry and cooldown policy

**Décision : TEST_COMPLETE — PASS**

### Commandes exécutées

```
python -m pytest tests/test_daemon_retry_cooldown.py -v   → 35/35 passed
python -m pytest --tb=short -q                            → 201/201 passed
```

### Critères d'acceptation

| Critère | Statut |
|---|---|
| Un `quota_exceeded` ne boucle pas infiniment | **PASS** — cooldown 1h persisté, `_is_blocked_by_retry` bloque le re-lancement |
| Les retries sont limités et traçables | **PASS** — max 5 retries (exponential) / max 3 retries (fixed_delay), `retry_count` persisté |
| Les cooldowns sont persistés | **PASS** — `retry-state.json` écrit atomiquement, rechargé à chaque cycle daemon |
| Les logs daemon sont explicites | **PASS** — chaque décision logge ticket_id, failure_class, action, délai, `human attention` si stop |
| Les tests couvrent les policies principales | **PASS** — 35 tests, toutes les 7 failure classes couvertes |
| Le workflow existant reste compatible | **PASS** — `run_ticket.py` / `run_step.py` non modifiés, 201/201 tests passent |

### Régressions

Aucune. Suite complète 201/201.

### Limites

- Persistance entre redémarrages du daemon non testée au niveau système (garantie par l'écriture fichier).
- `_read_last_failure_class` lit la dernière occurrence globale du log — risque mitigé car `_clear_retry_state` est appelé sur succès.

Le rapport complet est dans `runs/T025/test-report.md`. État passé à `TEST_COMPLETE`.
