# PR Review — T219 (attempt 2)

## Résumé

Les quatre actions du review-attempt-1 ont été traitées correctement dans
le commit `d4127ef4`. La logique applicative reste celle déjà validée
(routes batches read-only + actions guardées, pages dashboard, composants
React Flow, schémas Pydantic, polling 10 s), et les artefacts qui
polluaient le repo ont été supprimés à la source. Les suites dédiées
restent vertes (backend 17/17, frontend 19/19) et aucun nouvel artefact
parasite n'est créé pendant les tests.

## Vérifications effectuées

- Lecture du diff `d4127ef4` sur `.gitignore`, `tests/api/test_batches_routes.py`,
  `services/control_api/routes/batches.py:481`,
  `apps/dashboard/src/components/ProjectSidebar.jsx`, et de
  `apps/dashboard/node_modules/.vite/vitest/results.json`.
- `git ls-files | grep postgres:adf` → **aucun** fichier tracé (les deux
  artefacts SQLite ont disparu du tracking).
- `python -m pytest tests/api/test_batches_routes.py -q` → **17 passed**.
- Inspection post-pytest du worktree : aucun `postgres:adf#*` n'apparaît
  dans le CWD, donc le patch de fixture tient.
- `npx vitest run tests/BatchesPage.test.jsx tests/BatchDetailPage.test.jsx
  tests/BatchDependencyGraph.test.jsx` → **3 fichiers / 19 tests passed**.
- Comparaison `git show 65da148a:.../vitest/results.json` vs `git show
  d4127ef4:.../vitest/results.json` → contenu **strictement identique**
  (le coder a bien remis le cache à son état pré-T219).
- Suite adjacente `tests/test_ticket_dispatcher_api.py` : 22 passed / 2
  failed (`test_project_recommendations_in_advisory_mode`,
  `test_project_recommendations_mode_override`). Reproduction sur
  `HEAD~3` (avant T219) → **mêmes 2 échecs**, donc préexistants et
  indépendants de ce ticket (déjà noté dans review-attempt-1).

## Points validés (déjà couverts par attempt 1, toujours OK)

- Routes globales et project-scoped : `GET /dispatcher/batches`,
  `/current`, `/{id}`, `/{id}/graph`, `/{id}/phases`, `/{id}/insights` ;
  `POST /freeze`, `/retry-dependency-analysis`, `/recompute-dependencies`,
  `/cancel` + leurs variantes `/projects/{project_id}/...`.
- `409` sur transitions invalides (tests couverts).
- GET non mutants, POST via `transition_batch` / `update_backlog_batch` +
  `runtime_event` `batch.operator_action`.
- Color mapping `_ticket_color_key` couvre les 6 clés, `_current_phase`
  ne progresse que sur phase entièrement DONE.
- Graph : dédoublonnage des conflits, filtrage hors-batch, alias
  Pydantic `from`/`to` via `response_model_by_alias=True`.
- Frontend : `usePolling(fetchAll, 10000, …)`, boutons désactivés selon
  statut, erreur backend remontée dans `ErrorBanner`.

## Résolution des actions précédentes

1. **`postgres:adf#ai-dev-factory` retiré + `.gitignore` étendu** —
   `.gitignore:84-87` ajoute `postgres:adf#*` avec un commentaire qui
   trace l'origine (PgHandle.__str__ → sqlite3.connect). Les deux blobs
   (`postgres:adf#ai-dev-factory`, `postgres:adf#proj-a` hérité de T218)
   sont supprimés du tracking.
2. **Fixture `_make_app` patchée** — `tests/api/test_batches_routes.py:93`
   ajoute `"resolve_db_path_for_project"` à la liste d'attributs
   réécrits sur `live_db` avec la version SQLite. Vérifié *in vivo* :
   après pytest, aucun `postgres:adf#*` n'est créé.
3. **Cache vitest restauré** — diff entre `65da148a` et `d4127ef4`
   = vide. Net effet de T219 sur ce fichier : 0.
4. **N+1 dans `_build_insights`** — `routes/batches.py:481` hisse
   `runtime_map = _ticket_runtime_map(db_path)` hors de la boucle ;
   l'usage à `routes/batches.py:486` lit la map déjà calculée.
5. **Bonus** : sidebar `NavLink` pour Dispatcher reçoit `end: true`
   (`ProjectSidebar.jsx:7`), le rendering threade `end` vers `NavLink`
   (`ProjectSidebar.jsx:80`). `/dispatcher/batches[…]` n'active plus à
   tort l'onglet Dispatcher.

## Risques restants

- **Tracking historique de `apps/dashboard/node_modules/`** : la
  modification incluse dans T219 a été annulée, mais le sous-arbre
  reste tracé sur la branche, ce qui fera périodiquement remonter du
  bruit dans les commits. Hors-scope T219 — à traiter par un
  `git rm --cached -r apps/dashboard/node_modules` dédié.
- **Graph layout** : déterministe par phase × index ; lisible jusqu'à
  ~30 nœuds, dégradation acceptable pour le MVP au-delà.
- **`recompute-dependencies`** : `update_backlog_batch` direct sans
  verrou optimiste (les statuts source sont multiples). Conforme au
  plan ; l'event opérateur conserve `previous_status` pour audit.

## Décision

- APPROVE

Tous les blocants de l'attempt précédent sont levés, la logique
applicative est inchangée et validée, le scope reste circonscrit aux
fichiers prévus par le plan, et les suites dédiées sont vertes.

IMPLEMENTATION_APPROVED
