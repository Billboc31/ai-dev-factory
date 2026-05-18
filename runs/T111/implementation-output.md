All tasks complete. Here's the implementation summary:

---

## Résumé — T111

### Fichiers créés

- **`tools/agent_runner/runtime_db.py`** — Module SQLite stdlib-only. 4 tables : `issue_intake`, `ticket_runtime`, `workers`, `runtime_events`. WAL mode. Résolution DB via `git rev-parse --git-common-dir` (fonctionne depuis les worktrees). Fonctions CRUD complètes.
- **`tests/test_runtime_db.py`** — 15 tests couvrant init, upsert, duplicate handling, workers, events, et persistance après reconnexion.

### Fichiers modifiés

- **`.gitignore`** — Ajout de `.runtime/`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`, `runs/.issue-intake.json`, `runs/workers.json`.
- **`tools/agent_runner/run_daemon.py`** :
  - Import `runtime_db` via importlib (pattern existant)
  - `save_issue_index()` : dual-write JSON + SQLite
  - `_register_worker()` / `_unregister_worker()` : aussi dans SQLite
  - `_cleanup_stale_workers()` : nettoie aussi SQLite
  - `poll_github_issues()` : **suppression de l'appel `_commit_after_intake()`** + `upsert_ticket_runtime()` après intake
  - `run_once()` : sync `upsert_ticket_runtime()` pour chaque ticket découvert
- **`tools/agent_runner/run_issue_intake.py`** : appel `_record_sqlite_intake()` après écriture du `state.json`
- **`services/control_api/services/board_service.py`** : lit workers et issue index depuis SQLite (fallback JSON)
- **`tests/test_daemon_issue_polling.py`** : mise à jour du test `_commit_after_intake` (la fonction n'est plus appelée)

### Critère principal atteint

Le daemon ne crée plus de commit parasite `intake — update issue index` sur `main`. L'index intake vit désormais dans SQLite (gitignored) et JSON local (gitignored).
