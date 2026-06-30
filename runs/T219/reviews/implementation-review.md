# PR Review — T219 (attempt 2)

## Résumé

Les quatre actions du review-attempt-1 ont été correctement adressées dans `d4127ef4`. La logique applicative reste celle déjà validée (routes batches read-only + actions guardées, pages dashboard, React Flow, polling 10 s) ; les artefacts qui polluaient le repo ont disparu à la source et aucun nouveau n'est créé pendant les tests.

## Vérifications effectuées

- `git ls-files | grep postgres:adf` → **aucun** fichier tracé.
- `pytest tests/api/test_batches_routes.py` → **17 passed**, et après la run le worktree ne contient pas de `postgres:adf#*` (fix de fixture validé *in vivo*).
- `vitest run` sur `BatchesPage.test.jsx` + `BatchDetailPage.test.jsx` + `BatchDependencyGraph.test.jsx` → **19 passed**.
- Diff `65da148a` vs `d4127ef4` sur `apps/dashboard/node_modules/.vite/vitest/results.json` → **strictement identique** (net effet T219 = 0).
- Suite adjacente `tests/test_ticket_dispatcher_api.py` : 2 échecs reproduits sur `HEAD~3` → préexistants, indépendants de T219.

## Résolution des actions

1. `postgres:adf#*` ajouté à `.gitignore:84-87` avec commentaire d'origine ; deux blobs supprimés du tracking.
2. `tests/api/test_batches_routes.py:93` patche `resolve_db_path_for_project` sur la version SQLite.
3. Cache vitest restauré au contenu pré-T219.
4. `routes/batches.py:481` hisse `runtime_map = _ticket_runtime_map(db_path)` hors de la boucle de `_build_insights`.
5. Bonus : `ProjectSidebar.jsx:7/80` ajoute `end: true` sur l'item Dispatcher, fix du highlight quand on visite `/dispatcher/batches`.

## Décision

**APPROVE** — tous les blocants de l'attempt précédent sont levés, scope respecté, suites dédiées vertes. Review écrite dans `runs/T219/reviews/review-attempt-2.md`.

IMPLEMENTATION_APPROVED
