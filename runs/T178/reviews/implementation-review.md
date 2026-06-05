---

# PR Review — T178 Supervisor runtime_root Override Fix

## Résumé

T178 ajoute les champs manquants `runtime_root` et `force_source_refresh` au modèle Pydantic `EnvironmentProvisionRequest` dans `services/supervisor/main.py`. Sans ces déclarations, Pydantic les ignorait silencieusement lors du `model_dump()`, causant un mode `auto` permanent dans `_resolve_runtime_root`. Le fix est chirurgical et direct.

## Vérifications effectuées

- Diff complet vs `main` pour les deux fichiers modifiés
- Cohérence avec le plan approuvé (plan.md)
- Couverture des critères d'acceptation du ticket
- Logique de validation des chemins
- Qualité et exhaustivité des tests
- Absence de régressions de scope

## Points validés

**Correction du root cause** — `EnvironmentProvisionRequest` déclare maintenant `runtime_root: str | None = None` et `force_source_refresh: bool = False` (`main.py:1260-1261`). C'est exactement le correctif nécessaire : Pydantic propageait désormais ces champs dans `model_dump()`.

**Validation à la frontière API** — La vérification chemin absolu + absence de `..` dans les parts (`main.py:1289-1297`) est correcte et cohérente avec les checks existants dans `_resolve_runtime_root`. Retourner HTTP 422 est le bon code de statut.

**Logging diagnostique** — Le log INFO avec masquage de `runtime_root` (`"<set>"` si présent, sinon `None`) répond directement aux demandes de diagnostic du ticket. Pas de fuite de valeur sensible dans les logs.

**Tests** — Deux tests ajoutés (`test_environment_supervisor.py:233-299`) :
- `test_supervisor_provision_forwards_runtime_root` : vérifie la propagation end-to-end jusqu'à `state.runtime_root` via mock de `deploy_operational_runtime`. Pattern cohérent avec les tests existants.
- `test_supervisor_provision_rejects_relative_runtime_root` : vérifie le rejet HTTP 422. Assertion sur le message d'erreur.

**Conformité au plan** — Toutes les inclusions du plan sont implémentées. Toutes les exclusions sont respectées (pas de changements à `environment_provision.py`, `sandbox_runtime_deploy.py`, `SandboxState`, ni au control API).

**Critères d'acceptation** — Les 4 critères vérifiables par code/test sont satisfaits. Le 5ème (log `runtime_root_source=override` end-to-end) dépend du code existant dans `sandbox_runtime_deploy.py` qui n'avait pas besoin d'être modifié — cohérent avec l'analyse du plan.

## Problèmes détectés

**Mineur — Import `pathlib.Path` en milieu de fonction** (`main.py:1291`) :

```python
from pathlib import Path as _Path
```

Cet import est effectué dans le corps de la fonction plutôt qu'au niveau du module. Ça fonctionne, mais c'est contraire aux conventions Python standard. `pathlib` est une stdlib, aucune raison de différer l'import. Pas bloquant.

**Mineur — Pas de test pour chemin avec `..`** — La logique `".." in _Path(rr).parts` est correcte et couvre les cas comme `/abs/../etc`, mais il n'y a pas de test explicite pour ce vecteur. Pas bloquant compte tenu de la simplicité du check.

## Risques éventuels

Aucun risque identifié. La modification est additive (ajout de champs optionnels avec valeur par défaut, ajout de validation). Elle ne change aucun comportement existant pour les appels qui n'envoient pas `runtime_root`.

## Décision

APPROVED — Correctif minimal, ciblé, conforme au plan, tests pertinents. Les deux observations sont mineures et ne justifient pas de bloquer le merge.

## Actions demandées

- (optionnel) Déplacer `from pathlib import Path as _Path` en haut du fichier avec les autres imports stdlib.

---

IMPLEMENTATION_APPROVED
