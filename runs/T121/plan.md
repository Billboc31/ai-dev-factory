Le plan est écrit à `runs/T121/plan.md`. Voici le résumé :

---

**Diagnostic** : Le bug central est dans `daemon_manager.py` — il appelle `project_root / "runs"` en dur (lignes 29, 33, 81, 153) au lieu d'utiliser `resolve_runs_dir()` / `resolve_worktrees_dir()` qui existent déjà dans `runtime_resolver.py`. Quand la Control API tourne depuis le worktree `worktrees/T121/`, le PID est cherché au mauvais endroit et le daemon est démarré avec le mauvais `cwd`.

**6 changements prévus** :

| Fichier | Quoi |
|---|---|
| `services/control_api/services/daemon_manager.py` | Fix chemins via `resolve_runs_dir` + `resolve_worktrees_dir` + `sync_main()` + workers |
| `services/control_api/models/schemas.py` | Ajouter `workers: list[str]` à `DaemonStatus` |
| `services/control_api/routes/daemon.py` | Exposer `POST /daemon/sync-main` |
| `apps/dashboard/src/api/daemon.js` | Ajouter `syncMain()` |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Boutons Sync Main + Refresh, affichage workers, propagation erreurs |
| `.gitignore` | Ajouter `runs/*/prompts/` |
