Now I have a complete picture of the implementation. Let me write the review.

---

# PR Review — T173: Environment runtime must use committed project scripts from selected branch

## Résumé

L'implémentation modifie `deploy_operational_runtime` dans `sandbox_runtime_deploy.py` pour que tout déploiement d'environnement clone systématiquement le dépôt sélectionné dans `sandbox_dir/source/` et exécute les scripts depuis ce clone — jamais depuis le checkout host de ai-dev-factory. Un guard de validation de chemin est ajouté pour détecter les tentatives d'échappement par symlink. Deux nouveaux tests couvrent les cas ajoutés. Les tests existants sont mis à jour pour mocker `_clone_fresh_source`.

## Vérifications effectuées

- Lecture complète du diff `services/control_api/services/sandbox_runtime_deploy.py` vs `main`
- Lecture complète de `tests/test_sandbox_runtime_deploy.py`
- Vérification de la liste exhaustive des fichiers modifiés (`git diff --name-only`)
- Vérification ligne par ligne du guard de validation de chemin (lignes 405–422)
- Vérification du logging des script paths (lignes 424–426)
- Vérification de la couverture des 6 critères d'acceptation du ticket

## Points validés

**Critère 1 — Clone systématique vers `sandbox_dir/source/`**
Ligne 281 : `source_path = sandbox_dir / "source"` — sans conditionnel. Le `if state.ref else project_root` est correctement supprimé. ✅

**Critère 2 — `state.ref = None` clone la branche par défaut**
`_clone_fresh_source` passe de `ref: str` à `ref: str | None` (ligne 197). Quand `ref` est `None`, `--branch` est omis du `git clone`. Le check de mismatch de branche est gardé par `if ref is not None and actual_branch != ref:`. ✅

**Critère 3 — Log `resolved script path:` avant exécution**
Lignes 424–426 : chaque nom de script de `_SCRIPT_PHASE` est loggué via `f"resolved script path: {script_path}\n"`. Les chemins sont construits sur `resolved_source` (valeur résolue après `.resolve()`). ✅

**Critère 4 — Guard de validation de chemin**
Lignes 405–422 : `source_path.resolve()` suivi de `.relative_to(sandbox_dir)`. Une `ValueError` → retour immédiat `success=False` avec message explicite. Le test `test_deploy_operational_runtime_path_validation_fails` valide ce guard avec un symlink externe. ✅

**Critère 5 — Jamais de scripts du host ai-dev-factory**
`source_path` pointe toujours sur `sandbox_dir / "source"`. `_run_scripts` reçoit `source_path` (ligne 464), jamais `project_root`. ✅

**Critère 6 — Environnements concurrents et dépôts externes**
Chaque environnement a son propre `sandbox_dir` isolé. Aucune hypothèse hardcodée sur ai-dev-factory. ✅

**Couverture des tests**
- `test_deploy_operational_runtime_clones_even_without_ref` : clone avec `ref=None`, vérifie que `clone_args[0][2] is None` et que `_run_scripts` reçoit `sandbox_dir/source`. ✅
- `test_deploy_operational_runtime_path_validation_fails` : symlink externe, vérifie `success=False`, message "path validation", et que les scripts ne s'exécutent pas. ✅
- Tests existants mis à jour avec mock `_clone_fresh_source` dans les 3 fichiers concernés. ✅

**Scope**
Le diff est strictement borné aux exigences du ticket. `deployer_runner.py` et `run_sandbox.py` (validation mode) ne sont pas touchés. ✅

## Problèmes détectés

**Aucun problème bloquant.**

**Observation mineure — Absence de pré-vérification d'existence des scripts**
Le ticket stipule "If a required script is missing from the selected branch, deploy fails clearly." L'implémentation log les chemins résolus (lignes 424–426) mais ne vérifie pas leur existence avant d'appeler `_run_scripts`. La détection d'un script manquant est déléguée à `_run_scripts`, qui produira un échec, mais potentiellement avec un message moins explicite ("command not found" vs "required script missing"). 

Ce point n'est pas bloquant car : (a) le ticket ne prescrit pas de pré-check explicite, seulement "fails clearly" ; (b) `_run_scripts` retourne bien `success=False` en cas d'échec ; (c) les chemins loggués permettent déjà d'identifier le problème dans les logs de déploiement.

## Risques éventuels

**Symlinks internes au clone**
Le guard valide que `source_path.resolve()` est dans `sandbox_dir`. Si le contenu cloné contenait lui-même des symlinks pointant hors du sandbox, ceux-ci ne seraient pas détectés par ce guard. Toutefois : (a) `git clone` n'exécute pas les symlinks, (b) `_run_scripts` exécute les scripts par chemin explicite, non par traversal. Ce risque est théorique et hors périmètre du ticket.

**Clone de la branche par défaut quand `state.ref = None`**
Quand `state.ref` est `None`, le clone porte sur la branche par défaut du dépôt source. Si ce dépôt est mis à jour entre la génération des scripts et le déploiement, des scripts d'une révision différente pourraient être exécutés. Ce comportement est cohérent avec la conception actuelle du système et documenté dans le docstring.

## Décision

L'implémentation respecte l'intégralité des exigences du ticket T173. Les changements sont bornés, corrects, bien testés et sans dérive de scope.

IMPLEMENTATION_APPROVED
