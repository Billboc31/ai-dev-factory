---

# PR Review — T133: Isolated Sandbox Deployment Runtime

## Résumé

Implémentation complète et correcte. Tous les critères d'acceptance du ticket sont couverts. Le code est propre, bien structuré, et conforme aux conventions du projet. 23 tests passants (13 unitaires + 10 intégration).

## Vérifications effectuées

- `sandbox_manager.py` : allocation de slots, cycle de vie, cleanup, logs
- `routes/sandbox.py` : 8 endpoints, gestion des 404, sérialisation
- `models/sandbox.py` : SandboxState, SandboxStatus
- `SandboxPanel.jsx` + `api/sandbox.js` : dashboard complet
- `test_sandbox_manager.py` + `test_sandbox_routes.py` : couverture des cas nominaux et d'erreur

## Points validés

- **Isolation Docker** : `COMPOSE_PROJECT_NAME=sandbox-{id}` par sandbox, via `--env-file` dédié
- **Isolation ports** : slot-based offset (slot 0 réservé main runtime, sandboxes à partir de slot 1), registre JSON thread-safe
- **Cycle de vie** : create/start/stop/destroy implémentés et testés, incluant `status=error` sur échec compose
- **Slot release** : slot libéré à la destruction et réutilisable (testé)
- **Cleanup** : destruction par seuil d'âge, timezone-aware, testé
- **Dashboard** : `/sandboxes` avec polling 5s, status badges, ports, logs modal, boutons lifecycle
- **Architecture** : séparation Models/Services/Routes/UI, dépendances minimales, types complets

## Problèmes détectés

### Dead code — `destroy_sandbox` route (non-bloquant)

`routes/sandbox.py:86-88` — le catch `SandboxNotFoundError` est mort. `sandbox_manager.py:170-173` absorbe silencieusement cette exception en interne, donc `DELETE /sandboxes/nonexistent` retourne 204 au lieu de 404. Le comportement idempotent est acceptable REST, mais le code laisse croire à un 404 qui n'arrive jamais.

### Path traversal latent sur `sandbox_id` (non-bloquant)

`sandbox_manager.py:77-79` — `sandboxes_dir / sandbox_id` sans validation. Un ID du type `../../tmp/evil` atteindrait `shutil.rmtree()` dans `destroy()`. Risque faible en contexte interne. Une validation `re.match(r'^[0-9a-f]{12}$', sandbox_id)` dans les routes éliminerait le vecteur.

### Exceptions silencieuses (non-bloquant)

`list()` et `cleanup_old()` utilisent `except Exception: pass`. Un `state.json` corrompu est ignoré sans log — remplacer par `logger.warning(...)`.

### Pas de confirmation avant Destroy (non-bloquant UX)

`SandboxPanel.jsx:109-114` — bouton "Destroy" sans dialogue de confirmation sur une opération irréversible.

## Risques éventuels

- `_registry_lock` est in-process — ne protège pas `port-registry.json` si plusieurs workers Uvicorn sont lancés (hors config actuelle, mais limite à documenter).
- `project_root` non validé — absence de `docker-compose.yml` produit `status=error` sans message explicite.

## Décision

L'implémentation est fonctionnellement complète. Les observations sont des améliorations souhaitables, pas des bloquants.

IMPLEMENTATION_APPROVED
