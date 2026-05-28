I have all the information needed to write the review.

---

# PR Review — T157: Ensure deployer fetches and checks out the requested branch

## Résumé

L'implémentation ajoute à la pipeline de déploiement sandbox la récupération explicite du ref remote, la résolution via SHA, et la persistance de métadonnées d'identité. 4 fichiers de production modifiés, 5 nouveaux tests. Toutes les exigences du ticket sont couvertes.

## Vérifications effectuées

- Lecture complète des diffs sur les 4 fichiers modifiés (`sandbox.py`, `deployer.py`, `sandbox_manager.py`, `test_sandbox_worktree.py`)
- Vérification du flux complet : route → `run_deploy_sandboxed` → `create_with_worktree` → `_do_deploy`
- Confirmation que `_do_deploy` utilise `sandbox.worktree_path` comme `cwd` (ligne 260 de `deployer_runner.py`)
- Vérification du comportement de cleanup en cas d'erreur (fetch fail, rev-parse fail, worktree add fail)
- Vérification de la persistance sur disque et du rechargement des métadonnées

## Points validés

**1. Fetch avant checkout**
`git fetch origin <branch>` est exécuté explicitement avant toute création de worktree. Le SHA est résolu via `git rev-parse origin/<branch>` après le fetch. L'ordre est vérifié par `test_create_with_worktree_fetches_before_checkout`.

**2. Checkout déterministe sur SHA**
`git worktree add --detach <path> <sha>` utilise le SHA résolu, pas le nom de branche local. Garantit que le worktree HEAD correspond exactement au dernier commit remote fetché. Vérifié par `test_create_with_worktree_uses_remote_sha_not_branch_name`.

**3. Déploiement depuis le worktree**
`_do_deploy` utilise `Path(sandbox.worktree_path)` comme `cwd` quand un sandbox est fourni (ligne 260 de `deployer_runner.py`). Le déploiement s'exécute bien depuis le code checké, pas depuis le clone principal.

**4. Persistance des métadonnées**
Trois champs ajoutés à `SandboxState` : `requested_ref`, `resolved_ref`, `commit_sha`. Écrits après création du worktree, rechargés via `status()`. La persistance round-trip est vérifiée par `test_create_with_worktree_records_ref_identity_in_state`.

**5. Échec explicite si branche inexistante**
Fetch failure → `RuntimeError` avec le nom de la branche dans le message, sandbox détruit (`len(mgr.list()) == 0`). Pas de fallback silencieux sur `main`. Couvert par `test_create_with_worktree_fails_loudly_if_fetch_fails`.

**6. Compatibilité descendante**
- Route sans `body.branch` → path `run_deploy` original inchangé
- `create_with_worktree` sans `branch` → comportement `--detach` identique à avant
- Les champs `SandboxState` sont optionnels avec `None` par défaut

**7. Sécurité git**
- `git fetch` uniquement sur le clone source (autorisé par les contraintes)
- Checkout isolé dans le worktree sandbox
- Appels subprocess en forme liste (pas de shell injection)
- Clone principal jamais muté

**8. Cleanup sur erreur**
`self.destroy(state.id)` appelé dans les deux chemins d'erreur (fetch fail et rev-parse fail) avant le `raise`. Si `create_with_worktree` lève, `sandbox` reste `None` dans `run_deploy_sandboxed` et le finally ne tente pas `mark_completed` sur un ID inexistant.

## Problèmes détectés

Aucun problème bloquant.

## Risques éventuels

**Mineur — Initialisation du singleton non atomique (`deployer.py` ligne 58-59)**

```python
if not hasattr(request.app.state, "_sandbox_manager"):
    request.app.state._sandbox_manager = SandboxManager()
```

Deux requêtes concurrentes pourraient créer deux instances `SandboxManager`. En pratique non-bloquant : `SandboxManager()` est idempotent (crée juste le répertoire) et le registre de ports utilise un lock fichier. Aucun comportement dangereux. L'utilisation d'un `threading.Lock()` serait plus propre mais n'est pas requise pour ce ticket.

**Mineur — Pas de test pour l'échec rev-parse**

`test_create_with_worktree_fails_loudly_if_fetch_fails` couvre le fetch fail mais il n'y a pas de test équivalent pour le cas où `git rev-parse` échoue (fetch réussi, ref non résolvable). Le comportement est correct dans le code, mais le test manquant est une lacune mineure de couverture.

**Mineur — Pas de validation du SHA retourné**

Si `rev_result.stdout.strip()` est vide avec returncode 0 (cas pathologique), l'erreur ne surgira que lors du `worktree add` avec un message moins clair. Une assertion explicite `if not commit_sha` amènerait un message d'erreur plus précis, mais la failure reste explicite.

## Décision

L'implémentation satisfait intégralement les exigences de T157 :
- Fetch remote avant création du worktree ✓
- Checkout déterministe sur SHA remote ✓  
- Persistance de `requested_ref`, `resolved_ref`, `commit_sha` ✓
- Échec explicite si branche inexistante ✓
- Déploiement effectif depuis le worktree checké ✓
- Compatibilité descendante main/non-branch ✓
- Tests couvrant les chemins critiques ✓

Les observations mineures (thread safety, test rev-parse) ne justifient pas de bloquer le merge.

## Actions demandées

Aucune action bloquante requise.

IMPLEMENTATION_APPROVED
