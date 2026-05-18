Le plan est écrit dans `runs/T111/plan.md`. Voici un résumé :

---

## Plan T111 — Résumé

**Problème racine** : `load_issue_index()` / `save_issue_index()` dans `run_daemon.py` écrivent `.issue-intake.json` puis le commitent sur `main` via `_commit_after_intake()`, ce qui fait diverger `main` local.

**Nouveau fichier** : `tools/agent_runner/runtime_db.py` — module SQLite stdlib avec 5 tables (`issue_intake`, `ticket_runtime`, `workers`, `runtime_events`, `runtime_metadata`), fonctions CRUD, WAL mode, résolution du chemin DB via `git rev-parse --show-toplevel`.

**9 étapes :**
1. Créer `runtime_db.py` avec schéma et CRUD complets
2. `.gitignore` — ajouter `.runtime/`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`
3. `run_daemon.py` — `load_issue_index()` lit SQLite + fallback JSON + import-on-first-read ; `save_issue_index()` écrit SQLite uniquement ; `_commit_after_intake()` — supprimer chirurgicalement le commit de l'index
4. `run_daemon.py` — `_register_worker()` / `_unregister_worker()` via SQLite
5. `run_daemon.py` — sync `upsert_ticket_runtime()` dans la fonction de transition d'état
6. `run_issue_intake.py` — enregistrer intake + ticket_runtime dans SQLite après ingestion
7. `board_service.py` — lire depuis SQLite, merger avec state.json fallback
8. `runtime_resolver.py` — lire `worktree_path` depuis SQLite en priorité
9. `tests/test_runtime_db.py` — 8 cas de test couvrant init, CRUD, duplicate, restart

**Hors scope V1** : locks SQLite, retry_state SQLite, runtime_metadata, suppression du JSON legacy, multi-projets.

**Risque principal** : résolution du chemin DB depuis un worktree et suppression chirurgicale de `_commit_after_intake()` sans casser d'autres commits légitimes.
