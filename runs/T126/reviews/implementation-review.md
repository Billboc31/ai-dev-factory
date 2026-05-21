---

# PR Review — T126: Fix dashboard 500 errors after project-scoped routing

## Résumé

L'implémentation est correcte sur les trois volets planifiés. Tous les critères d'acceptance sont satisfaits.

## Points validés

**Backend `main.py`** — Handler global `@app.exception_handler(Exception)` placé et câblé correctement. Imports `traceback`/`JSONResponse` ajoutés. Aucune modification du bloc `__main__` (pas de régression CLI).

**Backend `routes/daemon.py`** — `project_daemon_board` injecte maintenant `request: Request` et utilise `getattr(request.app.state, "worktrees_dir", None) or resolve_worktrees_dir(project_root)`, identique au pattern du handler legacy. Root cause corrigée.

**Backend `routes/project_map.py`** — `project_refresh_project_map` applique le même pattern. Les routes `project_get_project_map` et `project_get_project_map_activity` n'ont pas besoin de `worktrees_dir` — absence de modification justifiée.

**Backend `project_map_service.py`** — Pas de changement T126. Code existant déjà défensif : `_load_json` retourne `None` sur fichier absent ou JSON invalide, les deux getters retournent un objet vide. Conforme au plan.

**Frontend `IssueMapperActivityPage.jsx`** — Accepte `{ projectId }`, le passe à `mapApi.getProjectMapActivity(projectId)`, `projectId` dans les dépendances `useCallback`. Pas de closure stale.

**Frontend `App.jsx`** — `<IssueMapperActivityPage projectId={activeProject} />` aligné sur tous les autres composants page.

**API client `projectMap.js`** — `_pfx(null) === ''` fallback vers la route legacy `/project-map/activity` quand aucun projet n'est sélectionné. Comportement conforme à la spec du plan.

**Tests** — 9 tests couvrant board, project-map, activity, refresh (200 + 404 pour chaque), et le handler global 500. Isolation propre avec `tmp_path` + `raise_server_exceptions=False`.

## Problèmes détectés

Aucun problème bloquant introduit par T126.

**Observation hors-scope (pré-existant) :** `daemon_restart` legacy référence `exec_cmd` non définie dans son scope — bug existant avant T126, à traiter dans un ticket dédié.

## Décision

L'implémentation est correcte, bornée au scope du ticket, et couvre tous les critères d'acceptance. Aucune dérive de scope, aucune violation architecture, aucune régression introduite.

IMPLEMENTATION_APPROVED
