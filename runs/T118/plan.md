Le plan est écrit dans `runs/T118/plan.md`. Voici le résumé :

**3 fichiers à modifier, 3 étapes :**

1. **`schemas.py`** — ajouter `HeartbeatResponse` avec `timestamp_utc: str`, `runtime_root: str`, `daemon_running: bool`
2. **`routes/daemon.py`** — ajouter `GET /daemon/heartbeat` qui compose les trois champs depuis `datetime.now()`, `app.state.project_root`, et `daemon_manager.get_status().running`
3. **`tests/test_control_api_endpoints.py`** — deux cas de test (daemon stopped / daemon running via PID simulé)

Aucune nouvelle dépendance, aucun refactor, `main.py` non touché (le router daemon est déjà inclus).
