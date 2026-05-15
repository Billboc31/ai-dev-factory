Le plan est écrit dans `runs/T028/plan.md`. Voici le résumé :

---

## Plan T028 — Control API foundation

**Architecture** : `services/control-api/` avec FastAPI, structuré en 3 couches : routes / models / services.

**12 étapes** :
1. Scaffolding du module + `main.py` avec middleware logging
2. Modèles Pydantic (TicketSummary, DaemonStatus, ActionResult…)
3. `artifact_reader` — lecture seule de `runs/TXXX/` (jamais d'écriture)
4. `subprocess_runner` — wrapper contrôlé → `run_ticket.py` / `run_issue_intake.py` avec validation ticket_id
5. `daemon_manager` — start/stop via PID file (`runs/daemon.pid`) + SIGTERM
6. Routes `/health` + `/daemon`
7. Routes `/tickets` (lecture artefacts)
8. Routes `/tickets` workflow (actions → subprocess, run-next en BackgroundTask)
9. Routes `/tickets` git actions (commit, push, checkpoint)
10. Routes `/issues` + `/providers`
11. Tests (3 fichiers dans `tests/`)
12. README

**Risques clés** :
- `run-next` est long (appel LLM) → 202 + BackgroundTask
- Daemon lancé hors API : PID file absent, stop impossible → limitation documentée
- Concurrence sur `state.json` → propagation des erreurs subprocess, pas de silencing

**Hypothèse importante** : `sys.executable` est utilisé dans subprocess_runner pour garantir le bon venv.
