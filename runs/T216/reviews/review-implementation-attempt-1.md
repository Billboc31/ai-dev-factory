# PR Review — T216 Implementation

## Résumé

L'implémentation suit strictement le plan approuvé. Trois changements ciblés :

1. `services/control_api/routes/settings.py:53-71` — docstring d'invariant + wrap `try/except` autour de `list_effective_settings(db)` qui logue (`logger.exception`) et retourne 500 plutôt que de laisser silencieusement passer une liste vide.
2. `tools/agent_runner/runtime_settings.py:34-40, 280-291` — ajout d'un `logger` module-level + registre `_warned_db_failures` qui logue une fois par clé en cas d'échec de lecture DB (comportement de fallback env/default inchangé).
3. `tests/test_control_api_settings.py:172-283` — cinq nouveaux tests bloquant le contrat empty-table (dont un qui `DROP TABLE runtime_settings` et vérifie que l'endpoint reste à 200 avec tous les `SETTING_SPECS`).

Aucune modification au frontend (`GlobalSettingsPage.jsx`), aux schémas Pydantic, ni à `runtime_db.py` — conforme au plan.

## Vérifications effectuées

- Lecture intégrale du diff (`git diff main` → 13 fichiers, dont 9 artefacts workflow + 4 fichiers de code).
- Exécution `pytest tests/test_control_api_settings.py` → **15/15 OK** (10 pré-existants + 5 nouveaux).
- Exécution `pytest tests/test_runtime_settings_registry.py tests/test_runtime_settings_db.py` → **20/20 OK**.
- Comparaison du `list_effective_settings` original sur `main` : il itérait déjà `SETTING_SPECS` avec fallback par clé → le contrat était déjà respecté côté logique. L'implémentation ajoute le filet de sécurité + l'observabilité + la couverture régression demandée par le ticket.
- Vérification des critères d'acceptation du ticket :
  - Fresh installation displays all settings → `test_list_returns_all_settings_on_empty_table`
  - Empty runtime_settings table still returns effective settings → idem + `test_list_survives_missing_runtime_settings_table`
  - Source column shows env/default → `test_list_source_is_default_when_no_env_no_db`, `test_list_source_is_env_when_no_db`
  - After saving, source changes to db → `test_list_source_switches_to_db_after_put`
  - Tests covering empty table scenario → 5 tests dédiés

## Points validés

- **Scope** : strictement borné au plan. Aucune dérive (pas de backfill, pas de cache, pas de touch frontend, pas de nouvelle clé `SETTING_SPECS`).
- **Architecture** : pas de modification structurelle. La logique de résolution `DB → env → default` reste centralisée dans `resolve_effective_setting`.
- **Observabilité** : `logger.exception` côté route + warn-once côté résolveur — la régression "liste vide silencieuse" deviendra visible en prod.
- **Sécurité** : aucun changement sur le traitement des clés sensibles. Le fallback env/default des secrets reste inchangé.
- **Tests** : couverture exhaustive du contrat empty-table, y compris le cas extrême `DROP TABLE`. Helper `_clear_all_spec_env_vars` proprement isolé via `monkeypatch`.
- **Code quality** : commentaires brefs et justifiés (expliquent le *pourquoi* du try/except et du warn-once registry).

## Problèmes détectés

Aucun bloquant.

Observations mineures (non bloquantes) :

- Le ticket diagnostique "GET /api/settings returns an empty list" mais le code original sur `main` itérait déjà `SETTING_SPECS`. Le coder l'a noté correctement dans `implementation-output.md` ("Limits / hypotheses") — le diagnostic du ticket était imprécis, et l'implémentation choisit la stratégie défensive (logs + tests de régression). C'est le bon arbitrage compte tenu du plan.
- `_warned_db_failures` est process-global et n'est pas reset entre tests. Documenté dans le code et dans `implementation-output.md`. Pas d'impact sur les tests actuels (chemin nominal) ni sur le runtime (warn-once est le comportement voulu).
- Le `except Exception` au niveau route (settings.py:65) est volontairement large — acceptable car logué via `logger.exception()` (stack trace complète), et tout le détail des erreurs par clé est déjà avalé en aval. Pas un anti-pattern dans ce contexte.

## Risques éventuels

- Vérification manuelle "fresh install docker-compose" listée dans les critères d'acceptation du plan non réalisée par le coder (limitation environnement). Couverte indirectement par `test_list_returns_all_settings_on_empty_table` et `test_list_survives_missing_runtime_settings_table` qui exercent le même chemin via TestClient. Risque résiduel : très faible — la branche frontale du dashboard `GlobalSettingsPage.jsx:250` reste comme garde-fou défensif (conforme au plan).
- Le warn-once est process-local : si plusieurs workers Uvicorn tournent en parallèle, chacun logera une fois par clé. Acceptable pour V1.

## Décision

- APPROVED

## Actions demandées

Aucune.

IMPLEMENTATION_APPROVED
