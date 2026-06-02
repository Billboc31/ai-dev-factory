I have enough information to write the review.

---

# PR Review — T165: Environment flows must ensure Traefik infra bootstrap

## Résumé

L'implémentation repose sur un audit de code qui a confirmé que la chaîne d'amorçage infra était déjà correctement câblée via le pipeline unifié `deploy_operational_runtime()`. Aucun changement de code de production n'a été nécessaire. Les changements produits sont exclusivement des tests ciblés qui vérifient le comportement requis par le ticket.

---

## Vérifications effectuées

- Lecture de `services/control_api/services/environment_provision.py` — `provision_environment()` (ligne 166) et `redeploy_environment()` (ligne 219) appellent toutes deux `deploy_operational_runtime()` sans sortie anticipée qui contournerait l'étape infra.
- Lecture de `services/control_api/services/sandbox_runtime_deploy.py` ligne 278 — `rs._ensure_required_infra(log_path)` est appelé **avant** le callback `_register_proxy_routes_after_compose()` et **avant** tout `_run_scripts()`.
- Vérification de `ProxyManager(auto_ensure_infra=False)` ligne 288-291 — empêche un double bootstrap lors de l'enregistrement des routes.
- Lecture de `tools/agent_runner/run_sandbox.py` lignes 247-252 — wrapper `_ensure_required_infra()` délègue à `infra_service_manager.ensure_required_infra()` sans réimplémentation.
- Lecture de `tests/test_environment_infra_bootstrap.py` — trois classes de test couvrant les trois scénarios du ticket.
- Lecture de `tests/test_environment_supervisor.py` lignes 106-168 — test end-to-end HTTP endpoint → `deploy_operational_runtime` → infra bootstrap.
- Vérification que `tests/test_sandbox_runtime_deploy.py` ligne 83 inclut `mock_infra.assert_called_once()`.
- Audit du git log : aucun fichier de production modifié — uniquement des fichiers de tests.

---

## Points validés

**Séquence d'exécution conforme au ticket**

```
ensure Traefik infra running      ← sandbox_runtime_deploy.py:278
→ ensure runtime network          ← infra_service_manager.ensure_runtime_network()
→ start.sh complète               ← run_scripts() avec callback on_step_complete
→ register routes                 ← _register_proxy_routes_after_compose()
→ healthchecks                    ← inclus dans les steps du pipeline
```

**Absence de duplication**

- Le seul point d'entrée canonique est `infra_service_manager.ensure_required_infra()`.
- `ProxyManager(auto_ensure_infra=False)` est correctement utilisé dans `_register_proxy_routes_after_compose()` pour éviter un deuxième appel.
- Aucune commande shell `bash deploy/infra/start_traefik.sh` n'est dupliquée hors de `TraefikManager._compose_up()`.

**Couverture des scénarios ticket**

| Scénario ticket | Test correspondant | Assertion clé |
|---|---|---|
| Traefik arrêté → démarre automatiquement | `TestTraefikInitiallyStopped` | `mock_ensure_running.assert_called_once()`, `result.success is True` |
| Redeploy avec infra arrêtée | `TestNoDuplicateBootstrap` (2ème invocation) + même pipeline | `mock_infra.call_count == 1` par invocation |
| Pas de double bootstrap | `TestNoDuplicateBootstrap` | call_count vérifié après `reset_mock()` |
| Endpoint HTTP → bootstrap | `test_provision_endpoint_triggers_infra_bootstrap` | `mock_infra.assert_called_once()` |

**Scope borné au ticket**

- Pas de changements à `traefik_manager.py`, `infra_service_manager.py`, `deployer_runner.py`.
- Pas de nouveau endpoint introduit.
- Pas de refactor transversal.

---

## Problèmes détectés

Aucun problème bloquant.

**Observation mineure (non-bloquante) :**

`TestTraefikInitiallyStopped` ne valide pas explicitement que `_ensure_required_infra` a été appelé — il vérifie seulement `TraefikManager.ensure_running`. Cela reste correct car si `ensure_running` est appelé, la chaîne est confirmée, mais une assertion `mock_run_sandbox_infra.assert_called_once()` parallèle aurait renforcé la couverture. Ce n'est pas un défaut bloquant car `TestInfraBootstrappedOnProvision` couvre déjà ce cas.

---

## Risques éventuels

**Faible.** L'absence de changements de production élimine tout risque de régression. Les tests ajoutés ne couvrent que des cas réels déjà testés unitairement par d'autres suites.

Le seul risque résiduel identifié par le plan — l'existence d'un endpoint `start` séparé qui contournerait `deploy_operational_runtime()` — a été audité et n'existe pas.

---

## Décision

L'implémentation respecte le ticket, le plan approuvé et les contraintes architecturales. Les tests couvrent les trois scénarios requis. Le code de production n'a pas été modifié inutilement — l'audit a correctement identifié que la logique était déjà en place. Aucun code dupliqué. Scope strictement borné.

IMPLEMENTATION_APPROVED
