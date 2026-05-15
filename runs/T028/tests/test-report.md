All three canonical scripts exist and the only `state.json` references in the service layer are read-only. I have enough to produce the final report.

---

# Test Report — T028: Control API Foundation

## Summary

**Result: PASS** — all acceptance criteria satisfied. 44 new tests pass, 237 pre-existing tests pass (no regressions).

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Le backend REST est dans un module séparé | **PASS** | `services/control_api/` — module distinct avec `main.py`, `routes/`, `models/`, `services/` |
| 2 | Les endpoints principaux existent | **PASS** | Tous les endpoints requis présents (health, daemon, tickets, issues, providers, projects) |
| 3 | Les actions appellent les scripts existants | **PASS** | `subprocess_runner.py` délègue à `run_ticket.py`, `run_daemon.py`, `run_issue_intake.py` via subprocess — scripts vérifiés présents |
| 4 | Aucune logique workflow n'est dupliquée | **PASS** | L'API ne contient aucune state machine — elle appelle uniquement les scripts existants |
| 5 | Aucune logique Git n'est dupliquée | **PASS** | Aucun appel `git` direct dans `services/control_api/` — commit/push/checkpoint passent par `run_ticket.py` |
| 6 | Les tickets et artefacts sont lisibles via API | **PASS** | `artifact_reader.py` expose `list_tickets`, `get_ticket`, `get_ticket_logs`, `get_ticket_artifacts`, `get_ticket_plan`, `get_ticket_review`, `get_ticket_tests` |
| 7 | Daemon start/stop fonctionne | **PASS** | `daemon_manager.py` — PID file, `Popen` detaché (`start_new_session=True`), SIGTERM pour stop, garde-fou "already running" |
| 8 | Les logs API sont explicites | **PASS** | Middleware HTTP logue chaque requête + méthode/path/status/ms ; actions critiques loguent `api: POST /tickets/…` |
| 9 | Les tests couvrent les endpoints critiques | **PASS** | 44 tests : endpoints HTTP, subprocess/validation, artefacts, daemon start/stop, mutation state.json interdite |
| 10 | Le workflow existant reste compatible | **PASS** | 237 tests pre-existants : 237/237 pass |

---

## Couverture des endpoints

Tous les endpoints du ticket sont implémentés :

```
GET  /health                                       ✓
GET  /daemon/status                                ✓
POST /daemon/start                                 ✓
POST /daemon/stop                                  ✓
POST /daemon/restart                               ✓
GET  /tickets                                      ✓
GET  /tickets/{ticket_id}                          ✓
GET  /tickets/{ticket_id}/logs                     ✓
GET  /tickets/{ticket_id}/artifacts                ✓
GET  /tickets/{ticket_id}/plan                     ✓
GET  /tickets/{ticket_id}/review                   ✓
GET  /tickets/{ticket_id}/tests                    ✓
POST /tickets/{ticket_id}/run-next                 ✓
POST /tickets/{ticket_id}/approve-plan             ✓
POST /tickets/{ticket_id}/request-plan-fix         ✓
POST /tickets/{ticket_id}/approve-implementation   ✓
POST /tickets/{ticket_id}/request-implementation-fix ✓
POST /tickets/{ticket_id}/commit                   ✓
POST /tickets/{ticket_id}/push                     ✓
POST /tickets/{ticket_id}/checkpoint               ✓
POST /issues/intake                                ✓
GET  /issues/intake/status                         ✓
GET  /providers/status                             ✓
GET  /projects                                     ✓
```

---

## Anomalies détectées

### Mineure — dead code dans `run-next` (non bloquant)

`routes/tickets.py:116` importe `BackgroundTasks` mais ne l'utilise pas ; `result_holder` est également créé mais jamais consommé. Le comportement fire-and-forget est correct via `threading.Thread`, mais le code mort peut prêter à confusion.

```python
from fastapi.background import BackgroundTasks  # importé, non utilisé
result_holder: list[ActionResult] = []          # créé, jamais lu
```

Impact : aucun — le endpoint fonctionne correctement. À nettoyer lors d'une prochaine passe.

---

## Validation finale

**281/281 tests pass.** Implémentation conforme aux critères d'acceptation. Aucun problème bloquant.
