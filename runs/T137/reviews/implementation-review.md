I have all the information needed. Here is the structured review.

---

# PR Review — T137: Sandbox Isolated Ports and UI Management

## Résumé

L'implémentation couvre l'ensemble du scope T137 : allocation de ports isolés par slot, fichier `deploy.env` sandbox, nommage compose unique, dashboard historique des runs avec logs et cleanup. La structure est propre, les patterns de robustesse sont cohérents avec les PRs précédentes. Deux problèmes requièrent un correctif avant merge.

---

## Vérifications effectuées

- `run_sandbox.py` : allocation/libération des ports, `_write_sandbox_env`, `_do_sandbox` complet
- `docker-compose.yml` : remappage des ports
- `services/control_api/routes/sandbox.py` : `runs_router` — 3 endpoints
- `services/control_api/models/schemas.py` : nouveaux champs
- `apps/dashboard/src/components/SandboxRunsPanel.jsx` : composant complet
- `apps/dashboard/src/pages/DeployerPage.jsx` : intégration
- Flux de cleanup de bout en bout

---

## Points validés

**Port isolation**
- Allocation par slots via fcntl : thread-safe et sans collision
- `finally: _release_port_slot(sandbox_id)` au bas de `_do_sandbox` garantit la libération dans tous les cas (y compris `return` intermédiaire dans le `try`)
- `docker-compose.yml` mis à jour : `${API_PORT:-8080}:8080` et `${WEB_PORT:-3000}:80`
- `COMPOSE_PROJECT_NAME=sandbox-{sandbox_id}` unique par run

**Env file**
- `deploy.env` créé avant la première écriture de state → ports visibles dès le début
- Contient les 7 variables demandées par le ticket

**API**
- Schémas backward-compatible (nouveaux champs avec defaults)
- 3 endpoints correctement gérés (404, 204, `lines` borné 1-10000)
- Filtrage des states sans `project_id`

**Dashboard**
- Affiche tous les champs requis : sandbox_id, project_id, state, timestamps, last_step, ports, worktree_path
- Actions : refresh manuel, logs modal (terminal dark), cleanup
- Cleanup désactivé pendant un run actif (`isRunning` guard)
- Auto-refresh toutes les 10s

---

## Problèmes détectés

### 1. BUG BLOQUANT — `project_root` absent de `state.json`

**Fichier** : `tools/agent_runner/run_sandbox.py:504-516`

`state_base` ne contient pas `project_root`. Or le cleanup (`sandbox.py:341`) lit `raw.get("project_root")` depuis `state.json` pour appeler `git worktree remove --force`. Ce champ étant toujours `None`, la condition `if project_root:` (ligne 343) est toujours fausse.

Conséquence : la commande git n'est jamais appelée. Le cleanup passe directement à `shutil.rmtree(worktree_path)`, ce qui supprime les fichiers mais **laisse l'entrée dans `.git/worktrees/`**. Après plusieurs cleanups, le dépôt accumule des entrées de worktrees fantômes qui :
- apparaissent dans `git worktree list`
- peuvent bloquer la recréation d'un worktree sur le même chemin
- dégradent l'état git du projet principal

**Correction requise** : ajouter `"project_root": str(project_root)` dans `state_base`.

```python
state_base = {
    ...
    "ports": ports,
    "worktree_path": str(worktree_path),
    "compose_project": compose_project,
    "project_root": str(project_root),   # ← à ajouter
}
```

---

### 2. SÉCURITÉ — Path traversal dans `sandbox_id`

**Fichier** : `services/control_api/routes/sandbox.py:328-332`

```python
sandbox_dir = sandboxes_root / sandbox_id
if not sandbox_dir.exists():
    raise HTTPException(status_code=404, ...)
```

`sandbox_id` n'est pas validé. Un appel `DELETE /sandbox-runs/..` produit `sandbox_dir = sandboxes_root / ".."` — soit le répertoire parent des sandboxes. `.exists()` retourne `True`, et `shutil.rmtree(sandbox_dir)` supprime tout le répertoire parent.

Le risque est atténué par le fait que l'API est interne, mais le vecteur existe dans l'état actuel.

**Correction requise** : valider le format de `sandbox_id` avant de construire le chemin.

```python
import re
if not re.fullmatch(r'[a-zA-Z0-9_\-]+', sandbox_id):
    raise HTTPException(status_code=400, detail="invalid sandbox_id")
```

---

## Risques éventuels (non bloquants)

**Race condition port registry** : `_release_port_slot_api` (API) n'utilise pas de file lock, alors que `_release_port_slot` (runner) l'utilise. Une libération simultanée runner + API pourrait corrompre le registre. Très improbable mais documenté.

**Locking subtil sur `_allocate_port_slot`** : le lock est acquis sur un `open("r+")`, mais si le fichier lock vient d'être créé par `touch()`, il est vide et `open("r+")` peut échouer sur certains OS. Faible risque en pratique.

**Auto-refresh infini en cas d'erreur API** : `SandboxRunsPanel` repoll toutes les 10s sans backoff ni circuit breaker. Non bloquant pour un outil interne.

**Pas de confirmation avant cleanup** : le bouton "Cleanup" est destructif sans modale de confirmation.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **[BLOQUANT]** Ajouter `"project_root": str(project_root)` dans `state_base` de `_do_sandbox` (`run_sandbox.py:504-516`)
2. **[BLOQUANT]** Valider `sandbox_id` (regex ou `re.fullmatch`) dans `cleanup_sandbox_run` avant de construire `sandbox_dir`

Ces deux corrections sont ponctuelles et n'affectent pas l'architecture de l'implémentation.

IMPLEMENTATION_FIX_REQUIRED
