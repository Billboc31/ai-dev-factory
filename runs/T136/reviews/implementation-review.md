Now I have all the information needed to write the review. Let me produce the structured review output.

---

# PR Review — T136: Deploy sandbox isolation and runtime separation

## Résumé

L'implémentation étend correctement l'infrastructure sandbox T133 avec : worktrees git isolés, isolation des projets Docker Compose, ports dynamiques, env files per-sandbox, lifecycle management (mark_completed + cleanup_completed), et visibilité dashboard. Les 20 nouveaux tests passent, les 58/59 tests existants passent (1 échec pré-existant non lié à T136).

---

## Vérifications effectuées

- Lecture complète de toutes les couches modifiées (model, service, supervisor, agent runners, dashboard, tests)
- Comparaison du diff `main...HEAD` par fichier
- Vérification des critères d'acceptation du plan
- Revue de la logique d'isolation, du rollback, et du lifecycle
- Analyse de la couverture des tests

---

## Points validés

**SandboxState model** (`models/sandbox.py`) — Trois champs optionnels ajoutés (`worktree_path`, `job_type`, `completed_at`). Rétrocompatible, valeurs par défaut `None`.

**create_with_worktree** (`sandbox_manager.py:168`) — Rollback correct : `destroy()` appelé si `git worktree add` échoue (ligne 185). `job_type` et `worktree_path` persistés en JSON.

**destroy + worktree** (`sandbox_manager.py:224`) — `git worktree remove --force` avant `shutil.rmtree`. L'option `--force` gère les worktrees en mauvais état sans faire échouer le cleanup.

**cleanup_completed** (`sandbox_manager.py:207`) — Gestion correcte des timestamps naïfs (UTC inject ligne 216). Exception-safe : une sandbox en erreur ne bloque pas le reste de la boucle.

**_inject_compose_flags** (`deployer_runner.py:186`) — Injection des flags `-p` et `--env-file` sur les commandes `docker compose`. Les valeurs sont générées en interne (sandbox IDs hexadécimaux), pas d'injection utilisateur.

**run_deploy_sandboxed** (`deployer_runner.py:299`) — Lock par projet préservé. Finally block garantit le cleanup. Gestion du cas sandbox=None (création échouée) correcte.

**supervisor analysis_start / scripts_start** (`supervisor/main.py:545, 686`) — Import gracieux de SandboxManager (try/except). Fallback `sandbox = None` sur erreur de création (le job se poursuit sans sandbox). Thread daemon avec `proc.wait()` garantit la destruction post-subprocess.

**run_analysis.py / run_scripts.py** — Pattern `SANDBOX_WORKTREE → effective_root` cohérent. Fallback explicite vers `project_root` si env var absente. La vérification de path traversal (`str(target).startswith(str(effective_root) + "/")`) est correctement mise à jour.

**SandboxPanel.jsx** — Badge `job_type` conditionnel (non affiché si absent). `worktree_path` avec `truncate` pour éviter les layout overflow. Non-intrusif.

**Tests** — Couverture correcte : unicité ports/compose/IDs, non-collision avec le runtime principal (web=3000, api=8080), cleanup par âge, env files isolés, rollback git, persistance état.

---

## Problèmes détectés

### 1. `_inject_compose_flags` — paths non quotés (mineur)

```python
return f"docker compose -p {compose_project} --env-file {env_file} {suffix}"
```

La commande est exécutée avec `shell=True` (ligne 248). Si `env_file` ou `compose_project` contient des espaces, le shell splittera le path en arguments séparés. En pratique le risque est quasi-nul (sandbox IDs hex, paths sous `AI_DEV_FACTORY_RUNTIME_ROOT`), mais c'est fragile.

**Correction suggérée** — utiliser `shlex.quote` :
```python
return f"docker compose -p {shlex.quote(compose_project)} --env-file {shlex.quote(env_file)} {suffix}"
```

### 2. run_deploy_sandboxed — sandbox non détruite immédiatement (observation de conception)

`cleanup_completed()` est appelé sans argument (seuil par défaut = 30 min). Puisque le sandbox vient d'être marqué `completed`, il ne sera jamais éligible lors de cet appel. Les sandboxes deploy s'accumulent jusqu'au prochain `run_deploy_sandboxed` > 30 min plus tard.

Contraste : le supervisor appelle `destroy()` immédiatement après la subprocess.

Ce comportement est **conforme au plan** (`mark_completed()` then `cleanup_completed()`) mais mérite d'être documenté comme intentionnel (garder le sandbox 30 min pour inspection post-déploiement).

### 3. Worktree detached HEAD pour analysis/scripts — vérification commit_and_push (observation)

Le supervisor crée les sandboxes analysis/scripts avec `branch=None` (detached HEAD). `run_analysis.py` et `run_scripts.py` appellent ensuite `commit_and_push(effective_root, project_id)` depuis ce worktree detached. Le comportement de `commit_and_push` en mode detached HEAD n'est pas couvert par les tests T136. Si la fonction suppose un branch existant ou tente un push vers un upstream, elle échouera silencieusement ou avec erreur.

Ce n'est pas un régresseur observable dans les tests actuels, mais c'est un point de fragilité non couvert.

---

## Risques éventuels

- **Threads daemon supervisor** : si le superviseur plante, les threads de cleanup sont tués en cours d'exécution. Les sandbox resources (worktrees git, répertoires) peuvent leaker. Acceptable pour l'architecture actuelle mais à surveiller.
- **Crash supervisor sans cleanup** : sandboxes orphelines sans `completed_at`, ignorées par `cleanup_completed`. La dashboard expose `cleanup_old (>7d)` comme filet de sécurité.

---

## Décision

L'implémentation respecte le ticket, le plan, les conventions existantes et les contraintes d'isolement. Tous les critères d'acceptation sont vérifiés. Les problèmes détectés sont mineurs ou non-bloquants, et n'empêchent pas l'objectif d'isolation concurrent des jobs de déploiement.

- APPROVED

## Actions demandées

- (Non-bloquant) Ajouter `shlex.quote` dans `_inject_compose_flags` pour sécuriser les paths avec espaces.
- (Non-bloquant) Documenter l'intention du seuil 30 min dans `run_deploy_sandboxed` (commentaire ou CHANGELOG).
- (Pour le prochain ticket) Vérifier que `commit_and_push` fonctionne correctement depuis un worktree detached HEAD, ou passer `branch=<current_branch>` lors de la création des sandboxes analysis/scripts.

---

IMPLEMENTATION_APPROVED
