# PR Review — T219 (Backlog Batch dashboard with dependency graph)

## Résumé

L'implémentation couvre intégralement le périmètre du plan : nouvelles routes
read-only + actions guardées dans `services/control_api/routes/batches.py`
(global + project-scoped), pages dashboard `BatchesPage` / `BatchDetailPage`,
composants `BatchDependencyGraph` (React Flow), `BatchPhasesPanel`,
`DispatcherInsightsPanel`, client API `apps/dashboard/src/api/batches.js`,
ajout de l'entrée sidebar "Batches", et trois suites de tests neuves
(`tests/api/test_batches_routes.py`, `tests/BatchesPage.test.jsx`,
`tests/BatchDetailPage.test.jsx`, `tests/BatchDependencyGraph.test.jsx`).

Sept critères d'acceptation du ticket sont satisfaits et démontrés par tests
verts. Le scope reste circonscrit aux fichiers prévus côté code applicatif,
mais le commit inclut deux artefacts de pollution CWD qui ne devraient pas
être versionnés.

## Vérifications effectuées

- Lecture intégrale de `services/control_api/routes/batches.py` (1052 lignes)
  et des schémas Pydantic ajoutés (`services/control_api/models/schemas.py`
  L731-844).
- Câblage des routers vérifié dans `services/control_api/main.py:237-239`.
- Cohérence des helpers `runtime_db` / `backlog_batch` / `ticket_dispatcher`
  utilisés (signatures `list_backlog_batches`, `get_backlog_batch`,
  `list_backlog_batch_ticket_ids`, `get_dependency_analysis`,
  `BatchStatus`, `transition_batch`, `mark_dependency_analysis_attempt_started`,
  `get_recommended_tickets`).
- Lecture des pages et composants React, de la route ajoutée
  (`apps/dashboard/src/App.jsx:97-98`) et de la nav
  (`apps/dashboard/src/components/ProjectSidebar.jsx:7`).
- Exécution `pytest tests/api/test_batches_routes.py` → **17 passed**.
- Exécution `npx vitest run` sur les trois nouveaux fichiers → **19 passed**.
- Exécution des suites adjacentes potentiellement impactées
  (`tests/test_ticket_dispatcher_api.py`, `tests/test_backlog_batch.py`,
  `tests/test_daemon_batch_lifecycle.py`) : 2 échecs préexistants dans
  `test_ticket_dispatcher_api.py` confirmés indépendants de T219 (mêmes
  échecs sur HEAD~1).

## Points validés

- **Conformité au plan** : toutes les routes prévues sont présentes
  (`GET /dispatcher/batches`, `/current`, `/{id}`, `/{id}/graph`,
  `/{id}/phases`, `/{id}/insights` ; `POST /freeze`, `/retry-dependency-analysis`,
  `/recompute-dependencies`, `/cancel`), avec leurs variantes
  `/projects/{project_id}/dispatcher/batches[...]`.
- **Garde 409** : les quatre actions refusent correctement les transitions
  invalides (testé sur `freeze`, `retry-dependency-analysis`,
  `recompute-dependencies`, `cancel`).
- **Pas de mutation cachée** : les GET ne touchent jamais la DB ; les POST
  vont par `transition_batch` / `update_backlog_batch` et émettent un
  `runtime_event` `batch.operator_action`.
- **Color mapping et phases** : `_ticket_color_key` couvre les 6 clés
  (`done / running / waiting / waiting_human / failed / selected`) et
  `_current_phase` ne déclare une phase comme courante que lorsque tous
  ses tickets sont terminés.
- **Graph** : dédoublonnage des arêtes conflict (clé triée + tag), filtrage
  des dépendances hors-batch, alias Pydantic `from`/`to` géré via
  `response_model_by_alias=True`.
- **Frontend** : `usePolling(fetchAll, 10000, …)` respecté ;
  `BatchActions` désactive chaque bouton selon le statut, surface l'erreur
  backend dans `ErrorBanner` (test `surfaces backend 409 errors`).
- **Légende** : le composant `ColorLegend` du detail expose un
  `data-color-key` par clé, vérifié par le test.
- **Pas de régression** dans `DispatcherPage` (route existante intacte) ni
  dans l'API dispatcher (suites associées toujours vertes là où elles
  l'étaient avant T219).

## Problèmes détectés

### Bloquant — pollution du repo par un artefact SQLite

Le commit `2520c4bc` ajoute le fichier `postgres:adf#ai-dev-factory` à la
racine du projet (4 KiB, SQLite vide). Il provient de l'exécution des tests
sur un hôte où `RUNTIME_DB_BACKEND=postgres` est défini : la fixture
`_make_app` (tests/api/test_batches_routes.py:54-93) ne patche pas
`runtime_db.resolve_db_path_for_project`, donc la résolution project-scoped
renvoie un `PgHandle` dont `__str__` produit `postgres:adf#<id>` (cf.
`tools/agent_runner/runtime_db_pg.py:349`). Les fonctions SQLite réinjectées
ensuite tentent un `sqlite3.connect(...)` sur cette chaîne, créant un
fichier au nom littéral dans le CWD. Ce fichier ne match pas `*.sqlite` de
`.gitignore` et atterrit dans le commit.

Actions requises :
- supprimer `postgres:adf#ai-dev-factory` du tracking
  (`git rm --cached postgres:adf#ai-dev-factory`) et l'ignorer
  (`postgres:adf#*` dans `.gitignore`, où il faut aussi traiter le
  `postgres:adf#proj-a` hérité de T218 pour cohérence) ;
- corriger la fixture pour que les routes project-scoped passent par le
  module SQLite : `setattr(live_db, "resolve_db_path_for_project", _sqlite_db.resolve_db_path_for_project)`
  dans la boucle de patch. Sinon n'importe quelle prochaine itération du
  worker recréera un artefact similaire.

### Bloquant — fichier de cache vitest committé

Le commit modifie aussi `apps/dashboard/node_modules/.vite/vitest/results.json`
(et `…/.package-lock.json`). `apps/dashboard/node_modules/` est listé dans
`.gitignore` mais 6880 fichiers du sous-répertoire restent tracés
historiquement, ce qui rend le diff trompeur : tout `npm install` ou run
vitest se retrouve embarqué. T219 n'a pas créé la situation, mais y
contribue en versionnant deux nouvelles écritures.

Action requise :
- ne pas inclure dans ce PR la modification de
  `apps/dashboard/node_modules/.vite/vitest/results.json` (purement
  cache de run). Idéalement, exécuter un `git rm --cached -r apps/dashboard/node_modules`
  séparément ; au minimum revert ces deux paths du commit T219.

## Risques éventuels

- **N+1 dans `_build_insights`** (`routes/batches.py:482-493`) :
  `_ticket_runtime_map(db_path)` est invoqué dans la boucle des tickets, ce
  qui re-scane `ticket_runtime` à chaque itération. Pour un batch de 30
  tickets avec ~100 tickets en base on déclenche ~3000 lectures par
  requête, multipliées par le polling 10 s. Sortir l'appel avant la boucle
  (comme déjà fait dans `_build_ticket_details`) résout sans changement de
  comportement.
- **Highlight sidebar** : `NavLink to="dispatcher"` matche par défaut le
  préfixe → l'entrée "Dispatcher" reste active quand on visite
  `/dispatcher/batches[…]`. Cosmétique mais perturbant. Ajouter `end`
  sur l'item Dispatcher règle la chose ; à voir si on veut le faire dans
  ce ticket ou laisser comme tel.
- **Réinitialisation forcée par `recompute-dependencies`** : remet
  `dependency_analysis_attempts` à 0 et écrase
  `last_dependency_analysis_error` / `next_dependency_analysis_retry_at`
  via `update_backlog_batch` directement, sans verrou optimiste (pas de
  `transition_batch` puisque les statuts source sont multiples). C'est
  conforme au plan, mais à signaler dans le log d'audit si l'on veut
  rejouer plus tard ; l'event opérateur inclut bien `previous_status`,
  donc OK.
- **Graph layout** : positionnement déterministe par phase × index, lisible
  jusqu'à ~30 nœuds. Au-delà, sans groupement parallèle, l'empilement
  vertical reste serré ; acceptable pour le MVP.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. Retirer du commit T219 le fichier `postgres:adf#ai-dev-factory` et
   ajouter une entrée `postgres:adf#*` dans `.gitignore`.
2. Patcher `tests/api/test_batches_routes.py::_make_app` pour aliaser
   `live_db.resolve_db_path_for_project` sur le module SQLite, afin
   d'empêcher la recréation de l'artefact lors des runs futurs.
3. Reverter du commit la modification de
   `apps/dashboard/node_modules/.vite/vitest/results.json` (purement
   cache local).
4. (Optionnel mais recommandé) sortir l'appel `_ticket_runtime_map(db_path)`
   hors de la boucle dans `_build_insights` (`routes/batches.py:482-493`).

Une fois les points 1-3 traités, le PR est mergeable : la logique
applicative est correcte, les tests dédiés passent (backend 17/17,
frontend 19/19), et le scope du ticket est intégralement adressé.

IMPLEMENTATION_FIX_REQUIRED
