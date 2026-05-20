Le plan est écrit dans `runs/T120/plan.md`. Voici un résumé :

---

**T120 — Plan d'implémentation (5 fichiers, 6 étapes)**

**Constat** : `retry-state.json` existe déjà avec `failure_class`, `retry_count`, `cooldown_until`, `stopped`, `stop_reason`, mais rien n'est exposé côté API ni dashboard.

**Étapes** :

| # | Fichier | Changement |
|---|---|---|
| 1 | `schemas.py` | Nouveau modèle `RetryState` (+ `last_error`) + champ optionnel dans `TimelineResponse` |
| 2 | `artifact_reader.py` | `get_retry_state()` : lit `retry-state.json` + extrait le dernier `"runtime failure:"` du log |
| 3 | `artifact_reader.py` | `get_ticket_timeline()` alimente `retry_state` dans la réponse |
| 4 | `routes/tickets.py` | Endpoint `GET /tickets/{id}/retry-state` (404 si fichier absent) |
| 5 | `api/tickets.js` | `getTicketRetryState(id)` |
| 6 | `WorkflowTimeline.jsx` | Bandeau rouge (stopped) ou orange (cooldown) sous les étapes si `timeline.retry_state` présent |

**Hors scope** : historique multi-retries, reset depuis le dashboard, SQLite, modification du daemon.

**Risques** : faibles — tous les champs sont optionnels, lecture JSON atomique, backward-compatible.
