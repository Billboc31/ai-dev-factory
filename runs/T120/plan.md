Le plan est écrit à `runs/T120/plan.md`. Voici un résumé :

---

**T120 — Plan d'implémentation**

**Constat** : `retry-state.json` existe déjà (écrit par le daemon) avec `failure_class`, `retry_count`, `cooldown_until`, `stopped`, `stop_reason` — mais rien n'est exposé côté API ni dashboard.

**5 fichiers à modifier** :

| Étape | Fichier | Changement |
|---|---|---|
| 1 | `schemas.py` | Nouveau modèle `RetryState`, ajout dans `TicketSummary` et `TimelineResponse` |
| 2–3 | `artifact_reader.py` | Fonction `get_retry_state()` + alimentation dans les readers existants |
| 4 | `routes/tickets.py` | Nouvel endpoint `GET /tickets/{id}/retry-state` |
| 5 | `api/tickets.js` | `getTicketRetryState(id)` |
| 6 | `WorkflowTimeline.jsx` | Bloc retry inline dans l'onglet timeline |

**Hors scope** : écriture SQLite (`last_error`, `runtime_events`), historique multi-retries, actions de reset, modification du daemon.

**Risques faibles** : tous les champs sont optionnels (backward-compatible), lecture JSON atomique, `None` si fichier absent.
