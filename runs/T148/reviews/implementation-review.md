I have a complete picture. Writing the review now.

---

# PR Review — T148 : Generic sandbox undeploy lifecycle

## Résumé

L'implémentation introduit un lifecycle générique d'undeploy et de cleanup pour les sandbox runtimes. Le changement est borné au ticket, les critères d'acceptance sont tous couverts, et 17 nouveaux tests valident les cas nominaux et les cas limites.

## Vérifications effectuées

- Lecture complète de `undeploy_runner.py` (nouveau module)
- Lecture complète de `sandbox_manager.py` (méthode `destroy()` réécrite)
- Lecture des tests `test_undeploy_runner.py` et des 5 nouveaux tests `test_sandbox_manager.py`
- Vérification de l'extension du schéma `DeployProfile` dans `schemas.py`
- Vérification du parsing des sections `undeploy`/`cleanup` dans `deployer_runner.py`
- Vérification de `_run_stop_script()` dans `run_sandbox.py`
- Croisement de chaque critère d'acceptance du ticket

## Points validés

**Lifecycle générique et project-agnostic**
- `undeploy_runner.py` est découplé de tout hardcoding docker. Le fallback `docker compose down` est intentionnel et documenté, l'orchestrateur lui-même ne contient aucune logique docker spécifique.
- Les sections `undeploy:` et `cleanup:` dans `deploy.yml` sont optionnelles, rétrocompatibilité assurée.

**Ordonnancement destroy() correct**
1. SIGTERM supervisor → 2. run_undeploy (reverse order) → 3. run_cleanup + stale files → 4. git worktree remove → 5. mark destroyed → 6. release port slot → 7. rmtree  
L'ordre garantit qu'aucun service ne tourne pendant le nettoyage des fichiers.

**Idempotence**
- Chaque étape log un warning en cas d'échec sans interrompre la suivante.
- Double appel à `destroy()` testé et validé (test `test_cleanup_idempotency`).
- `run_cleanup()` ne lève pas si `runtime_root` est None ou inexistant.

**Fix "already running"**
- `_pid_alive()` dans `status()` détecte les superviseurs morts et passe l'état à `stopped`.
- Les nouveaux sandbox utilisent des UUIDs distincts — aucun risque de collision.
- `test_recreate_sandbox_after_cleanup` confirme le comportement.

**Suppression des fichiers stale**
- `run_cleanup()` globe `*.pid` et `*.lock` dans `sandbox_dir` et `runtime_root`.
- Tests `test_stale_pid_removed` et `test_stale_lock_removed` valident les deux chemins.

**Stop script**
- `_run_stop_script()` exécuté dans le `finally` de `run_sandbox.py`, avant l'arrêt du supervisor.
- Tolérant aux erreurs (non-zero exit, timeout, absence du script).

**Couverture tests**
- 12 tests `test_undeploy_runner.py` couvrent reverse order, fallback, docker-type, idempotence, stale files, hooks, runtime_root manquant, stop.sh.
- 5 tests `test_sandbox_manager.py` couvrent compose down, SIGTERM ordering, worktree remove, idempotence, recreate.

## Problèmes détectés

**Mineur — Duplication de `_pid_alive()`**
La fonction est définie deux fois :
- `services/control_api/services/sandbox_manager.py:45`
- `services/control_api/services/deployer_runner.py:129`

Aucun impact fonctionnel, mais c'est une duplication silencieuse. Non bloquant.

**Mineur — `stop()` duplique une logique que `run_cleanup()` généralise**
`sandbox_manager.py:192-199` : `stop()` retire inline les `*.pid`/`*.lock` du `runtime_root` uniquement. `run_cleanup()` couvre `sandbox_dir` **et** `runtime_root`. Les deux méthodes font donc des choses légèrement différentes pour les stale files, sans que la différence soit documentée. Non bloquant pour ce ticket.

**Mineur — Cleanup hooks docker-type silencieusement ignorés**
`undeploy_runner.py:124` : les steps de type `docker` dans la section `cleanup:` sont silencieusement skippés (seul `type == "host"` est exécuté). Ce n'est pas documenté dans le schéma ni dans les logs. Un auteur de `deploy.yml` pourrait définir un cleanup docker et ne voir aucun effet. Non bloquant — acceptable pour une V1.

**Mineur — Chemin `env_file` non quoté dans la commande shell**
Dans `_run_step()` et la fallback de `run_undeploy()`, la commande est construite avec f-string et exécutée via `shell=True`. Le chemin `env_file` (`str(sandbox_dir / ".env")`) est basé sur un UUID hexadécimal sans espaces — en pratique safe. Mais si un futur changement introduit des espaces dans les chemins, la commande shell se briserait silencieusement. Non bloquant.

## Risques éventuels

**Pas de SIGKILL en fallback après SIGTERM**
`_terminate_sandbox_supervisor()` envoie SIGTERM mais ne vérifie pas si le processus s'est effectivement arrêté, et n'envoie pas de SIGKILL. Si le supervisor ignore SIGTERM, il reste en vie pendant l'undeploy. Ce comportement préexistait au ticket T148 — ce n'est pas une régression introduite ici. À adresser dans un ticket futur si nécessaire.

**Timeout 120s par étape**
Avec N étapes d'undeploy, le destroy peut prendre N×120s maximum. Acceptable pour des runtimes de développement.

## Décision

- APPROVED

L'implémentation est correcte, bien testée, et conforme à l'ensemble des critères d'acceptance du ticket. Les problèmes détectés sont tous mineurs et sans impact sur la fonctionnalité livrée. Aucune dérive de scope. Aucune violation architecturale.

IMPLEMENTATION_APPROVED
