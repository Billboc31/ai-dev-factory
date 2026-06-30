# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T219/reviews/implementation-review.md
- generated at: 2026-06-30T18:06:35Z

---

# PR Review

## Résumé

L'implémentation couvre intégralement le périmètre du plan : nouvelles routes read-only + actions guardées dans `services/control_api/routes/batches.py` (global + project-scoped), pages dashboard `BatchesPage` / `BatchDetailPage`, composants `BatchDependencyGraph` (React Flow), `BatchPhasesPanel`, `DispatcherInsightsPanel`, client API `apps/dashboard/src/api/batches.js`, ajout de l'entrée sidebar "Batches", et trois suites de tests neuves.

Sept critères d'acceptation du ticket sont satisfaits et démontrés par tests verts (backend **17/17**, frontend **19/19**). Le scope reste circonscrit aux fichiers prévus côté code applicatif, mais le commit inclut deux artefacts de pollution CWD qui ne devraient pas être versionnés.

## Vérifications effectuées

- Lecture intégrale de `services/control_api/routes/batches.py` (1052 L) et des schémas Pydantic ajoutés (`services/control_api/models/schemas.py:731-844`).
- Câblage des routers vérifié dans `services/control_api/main.py:237-239`.
- Cohérence des helpers `runtime_db` / `backlog_batch` / `ticket_dispatcher` utilisés.
- Lecture des pages et composants React, de la route ajoutée (`App.jsx:97-98`) et de la nav (`ProjectSidebar.jsx:7`).
- `pytest tests/api/test_batches_routes.py` → 17 passed.
- `npx vitest run` sur les trois nouveaux fichiers → 19 passed.
- Suites adjacentes (`test_ticket_dispatcher_api.py` etc.) : 2 échecs préexistants confirmés indépendants de T219 (mêmes échecs sur HEAD~1).

## Points validés

- Toutes les routes prévues sont présentes avec leurs variantes project-scoped.
- 409 correctement renvoyé sur les transitions invalides (testé).
- GET jamais mutants ; POST passent par `transition_batch` / `update_backlog_batch` + `runtime_event` `batch.operator_action`.
- Color mapping couvre les 6 clés, `_current_phase` n'incrémente que sur phase entièrement DONE.
- Graph : dédoublonnage des arêtes, filtrage hors-batch, alias Pydantic `from`/`to` géré via `response_model_by_alias=True`.
- Frontend : `usePolling(fetchAll, 10000, …)`, boutons désactivés selon statut, erreur 409 surfaceée dans `ErrorBanner`.
- `DispatcherPage` existant intact.

## Problèmes détectés

### Bloquant — artefact SQLite committé

Le commit ajoute `postgres:adf#ai-dev-factory` (4 KiB) à la racine. Origine : la fixture `_make_app` (tests/api/test_batches_routes.py:54-93) ne patche pas `runtime_db.resolve_db_path_for_project`. Sur un hôte avec `RUNTIME_DB_BACKEND=postgres`, la résolution project-scoped renvoie un `PgHandle` dont `__str__` produit `postgres:adf#<id>` (cf. `runtime_db_pg.py:349`) ; les fonctions SQLite réinjectées font alors `sqlite3.connect("postgres:adf#…")` qui crée le fichier dans CWD. `.gitignore` n'attrape pas ce nom.

Actions : `git rm --cached postgres:adf#ai-dev-factory`, ajouter `postgres:adf#*` à `.gitignore`, et compléter la fixture avec `setattr(live_db, "resolve_db_path_for_project", _sqlite_db.resolve_db_path_for_project)`.

### Bloquant — cache vitest committé

Modif de `apps/dashboard/node_modules/.vite/vitest/results.json` embarquée dans le commit (purement local). Le sous-arbre `node_modules` était déjà tracé historiquement malgré le `.gitignore`, mais T219 ne devrait pas y contribuer davantage. Reverter cette modification du commit.

## Risques éventuels

- **N+1 dans `_build_insights`** (`routes/batches.py:482-493`) : `_ticket_runtime_map(db_path)` réinvoqué dans la boucle. À sortir avant la boucle.
- **Sidebar** : `NavLink to="dispatcher"` reste actif sur `/dispatcher/batches[…]` (préfixe). Ajouter `end` règle la chose.
- **`recompute-dependencies`** : utilise `update_backlog_batch` direct sans verrou optimiste (statuts source multiples). Conforme au plan ; l'event opérateur enregistre `previous_status`.
- **Graph layout** : empilement par phase × index lisible ~30 nœuds ; acceptable pour MVP.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. Retirer `postgres:adf#ai-dev-factory` du commit + entrée `postgres:adf#*` dans `.gitignore`.
2. Patcher `_make_app` pour aliaser `resolve_db_path_for_project` sur la version SQLite (anti-récidive).
3. Reverter la modif de `apps/dashboard/node_modules/.vite/vitest/results.json`.
4. (Optionnel) sortir `_ticket_runtime_map` de la boucle dans `_build_insights`.

Review écrite dans `runs/T219/reviews/review-attempt-1.md`.

IMPLEMENTATION_FIX_REQUIRED
