The plan is written to `runs/T120/plan.md`. Here's a summary:

---

**T120 — Plan d'implémentation**

**7 fichiers, 6 étapes + tests.**

**Constat** : `retry-state.json` (`failure_class`, `retry_count`, `cooldown_until`, `stopped`, `stop_reason`) existe déjà mais n'est exposé nulle part.

**Étapes** :

| # | Fichier | Changement |
|---|---|---|
| 1 | `schemas.py` | Modèle `RetryState` + champ `retry_state: RetryState \| None` dans `TimelineResponse` |
| 2 | `artifact_reader.py` | `get_retry_state()` : lit JSON + extrait dernière ligne `runtime failure:` du log → `last_error` |
| 3 | `artifact_reader.py` | `get_ticket_timeline()` : alimente `retry_state` dans le retour |
| 4 | `routes/tickets.py` | `GET /tickets/{id}/retry-state` — 404 si fichier absent |
| 5 | `api/tickets.js` | Export `getTicketRetryState(id)` |
| 6 | `WorkflowTimeline.jsx` | Bandeau rouge (`stopped=true`) ou orange (`cooldown_until` défini) |
| 7 | Tests | 4 tests unitaires artifact_reader + 3 tests endpoint |

**Risques** : faibles — lecture seule, champs optionnels, backward-compatible.

**Hors scope** : historique retries, reset dashboard, modifications daemon/SQLite.
