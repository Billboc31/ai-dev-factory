# PR Review — T216 Implementation

## Résumé

L'implémentation suit strictement le plan approuvé. Trois changements ciblés :

1. **`services/control_api/routes/settings.py:53-71`** — docstring d'invariant + wrap `try/except` autour de `list_effective_settings(db)` qui logue (`logger.exception`) et retourne 500 plutôt que de laisser silencieusement passer une liste vide.
2. **`tools/agent_runner/runtime_settings.py:34-40, 280-291`** — ajout d'un `logger` module-level + registre `_warned_db_failures` qui logue une fois par clé en cas d'échec de lecture DB (fallback env/default inchangé).
3. **`tests/test_control_api_settings.py:172-283`** — cinq nouveaux tests verrouillant le contrat empty-table (dont un qui `DROP TABLE runtime_settings`).

Aucune modif frontend, schémas Pydantic ou `runtime_db.py` — conforme au plan.

## Vérifications effectuées

- Diff complet `git diff main` (4 fichiers de code + artefacts workflow).
- `pytest tests/test_control_api_settings.py` → **15/15 OK**.
- `pytest tests/test_runtime_settings_registry.py tests/test_runtime_settings_db.py` → **20/20 OK**.
- Tous les critères d'acceptation du ticket sont couverts par les nouveaux tests.

## Points validés

- **Scope** : strictement borné (pas de backfill, pas de cache, pas de touch frontend).
- **Observabilité** : `logger.exception` + warn-once — toute régression future "liste vide silencieuse" sera visible.
- **Sécurité** : traitement des clés sensibles inchangé.
- **Tests** : couverture exhaustive (empty table, missing table via `DROP`, env/default/db sources, PUT switch).

## Problèmes détectés

Aucun bloquant. Observations mineures (non bloquantes) :

- Le ticket diagnostique "GET retourne liste vide" mais le code original itérait déjà `SETTING_SPECS` ; l'implémentation choisit la stratégie défensive (logs + tests régression) — bon arbitrage.
- `_warned_db_failures` est process-global (documenté).
- Vérification manuelle `docker-compose` non réalisée (limitation environnement) ; couverte indirectement par les tests TestClient.

## Décision

APPROVED

IMPLEMENTATION_APPROVED
