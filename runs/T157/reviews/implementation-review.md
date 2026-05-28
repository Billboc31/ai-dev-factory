---

# PR Review — T157: Ensure deployer fetches and checks out the requested branch before deployment

## Résumé

L'implémentation ajoute la logique `git fetch` + `git rev-parse` + `git worktree add --detach <sha>` dans `sandbox_manager.create_with_worktree()`. Le déploiement d'une branche passe désormais par `run_deploy_sandboxed()` dans `deployer_runner.py`. Les trois champs d'identité (`requested_ref`, `resolved_ref`, `commit_sha`) sont ajoutés à `SandboxState` et persistés dans `state.json`.

## Vérifications effectuées

- Lecture complète de `sandbox_manager.py` (lignes 240–310)
- Lecture complète de `deployer_runner.py` (lignes 240–400)
- Lecture complète de `deployer.py` (routes)
- Lecture complète de `models/sandbox.py`
- Lecture complète de `tests/test_sandbox_worktree.py`
- Vérification de l'exposition des champs via `GET /sandboxes/{id}`
- Vérification de l'impact sur `GET /projects/{id}/deployer/status`

## Points validés

**Fetch + resolve avant checkout** — `git fetch origin <branch>` puis `git rev-parse origin/<branch>` sont bien appelés dans cet ordre avant `git worktree add`. (`sandbox_manager.py:260–284`)

**Checkout par SHA, pas par nom de branche** — `git worktree add --detach <path> <commit_sha>` garantit que le worktree pointe sur le commit exact fetché, indépendamment d'un éventuel déplacement de la branche locale. (`sandbox_manager.py:284`)

**Fail loudly** — Un fetch échoué ou un `rev-parse` échoué lève immédiatement `RuntimeError` avec le stderr git, et le sandbox est détruit avant de remonter l'erreur. Pas de fallback silencieux vers `main`. (`sandbox_manager.py:264–277`)

**Persistance de l'identité** — `requested_ref`, `resolved_ref`, `commit_sha` sont écrits dans `state.json` et relus correctement via `mgr.status()`. (`sandbox.py:33–35`, `sandbox_manager.py:296–305`)

**Logs** — Trois messages logger.info couvrent fetch, résolution SHA et création du worktree. (`sandbox_manager.py:256–282`)

**Chemin `main` préservé** — En l'absence de `branch`, l'appel reste sur `run_deploy()` sans aucun changement comportemental. (`deployer.py:67`)

**Tests** — 5 nouveaux tests unitaires dans `test_sandbox_worktree.py` couvrent : ordre fetch→checkout, usage du SHA vs nom de branche, fail loud sur fetch raté, persistance de l'identité sur disque, nettoyage du sandbox sur erreur.

**Exposition via API** — `SandboxState` avec les trois nouveaux champs est retourné par le `GET /sandboxes/{id}` existant. Les champs sont `None` pour les sandboxes créés sans branche, ce qui est rétrocompatible.

**Isolation sandbox** — Le lock partagé (`_get_lock(project_id)`) bloque correctement un deuxième deploy concurrent, qu'il soit sandboxed ou non.

## Problèmes détectés

### Mineur 1 — Statut deployer invisible pendant un branch deploy

Pendant `run_deploy_sandboxed()`, l'état est écrit dans `sandbox_dir/state.json`, pas dans le fichier projet `project_root/.ai-dev-factory/state.json`. En conséquence, `GET /projects/{id}/deployer/status` continue d'afficher l'état du dernier deploy non-sandboxé (pas `"running"`). Un appelant qui surveille cet endpoint ne verra pas le deploy en cours.

Le lock empêche correctement les deploys concurrents, mais la désynchronisation du statut peut induire des comportements inattendus côté outillage (ex. un agent ou une UI qui poll le statut et le voit comme "idle" alors qu'un deploy tourne).

### Mineur 2 — Sandbox ID absent de la réponse `trigger_deploy`

`POST /projects/{id}/deployer/deploy` retourne `ActionResult` (ok, message, error) mais pas l'ID du sandbox créé. Le ticket demande que la Runtime UI puisse afficher le ref et le SHA déployés depuis les métadonnées du sandbox. Pour l'instant, la UI devrait lister tous les sandboxes (`GET /sandboxes`) et filtrer par `ticket_id` pour retrouver le bon sandbox — fonctionnel mais non direct.

### Mineur 3 — `run_deploy_sandboxed` non testé

La fonction `deployer_runner.run_deploy_sandboxed()` n'a pas de test unitaire. Seule la couche `sandbox_manager` est couverte. Le comportement de propagation d'erreur de sandbox création vers `ActionResult`, le cleanup en `finally`, et l'injection des flags compose ne sont pas vérifiés par les tests.

### Cosmétique — Duplication de la création de `SandboxManager`

`deployer.py:60–62` recrée `SandboxManager()` en ligne alors que `sandbox.py` expose déjà `_get_manager(request)` pour exactement le même singleton sur `app.state._sandbox_manager`. Les deux chemins produisent le même résultat mais la duplication est fragile si la clé change ou si des arguments sont ajoutés.

## Risques éventuels

- Un deploy de branche via l'API ne met pas à jour le state fichier projet : si `run_ticket.py` ou un autre outil poll `deployer/status` pour savoir quand le deploy est terminé, il ne le verra jamais passer à `"completed"` ou `"failed"`.
- Le log de deploy sandboxé va dans `sandbox_dir/logs/deploy.log`, pas dans le log projet. `GET /projects/{id}/deployer/logs` ne montrera pas les logs d'un branch deploy.
- Ces deux points ne bloquent pas les critères d'acceptance directs du ticket mais peuvent causer des surprises en intégration.

## Décision

L'implémentation cœur est correcte et complète : fetch distant, résolution par SHA, checkout déterministe, fail loud, persistance de l'identité. Tous les critères d'acceptance du ticket sont satisfaits. Les problèmes détectés sont mineurs et n'invalident pas la sécurité ou la correction fonctionnelle de la feature.

- APPROVED

## Actions demandées

Aucune action bloquante. Pour le suivi :
1. Considérer l'ajout d'un test pour `run_deploy_sandboxed()` couvrant l'exception sandbox → `ActionResult` et le cleanup `finally`.
2. Envisager d'inclure `sandbox_id` dans `ActionResult` (ou une variante) pour permettre à la Runtime UI de pointer directement vers les métadonnées du sandbox déployé.
3. Documenter ou unifier la création du `SandboxManager` singleton entre `deployer.py` et `sandbox.py`.

IMPLEMENTATION_APPROVED
