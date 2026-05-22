I have all the information needed for a complete review. Both blocking issues from the previous review have been addressed. Let me write the structured review.

---

# PR Review — T137: Sandbox Isolated Ports and UI Management (retry)

## Résumé

Les deux problèmes bloquants signalés lors de la première review ont été corrigés. L'implémentation est complète et conforme au plan sur l'ensemble des 9 composants (A–I). Aucun nouveau problème bloquant identifié.

---

## Vérifications effectuées

- `run_sandbox.py` : `state_base`, allocation/libération ports, `_write_sandbox_env`, `_do_sandbox`
- `docker-compose.yml` : remappage des ports
- `services/control_api/routes/sandbox.py` : `runs_router` — 3 endpoints, validation `sandbox_id`
- `services/control_api/models/schemas.py` : nouveaux champs des deux schémas
- `services/control_api/services/sandbox_runner.py` : `_state_from_payload`
- `services/control_api/main.py` : enregistrement de `runs_router`
- `apps/dashboard/src/api/deployer.js` : fonctions T137
- `apps/dashboard/src/components/SandboxRunsPanel.jsx` : composant complet
- `apps/dashboard/src/pages/DeployerPage.jsx` : intégration

---

## Corrections des blockers précédents

### Fix 1 — `project_root` dans `state_base` ✓

`run_sandbox.py:517` contient maintenant `"project_root": str(project_root)`. Le cleanup (`routes/sandbox.py:343`) peut désormais appeler `git worktree remove --force` correctement au lieu de tomber silencieusement sur `shutil.rmtree` qui laissait des entrées fantômes dans `.git/worktrees/`.

### Fix 2 — Validation `sandbox_id` contre path traversal ✓

`routes/sandbox.py:330–331` valide le `sandbox_id` via `re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id)` avant toute construction de chemin. Un `DELETE /sandbox-runs/..` retourne maintenant 400 au lieu de supprimer le répertoire parent.

---

## Points validés

**Isolation ports (plan §A)**
- `_allocate_port_slot` : fcntl `LOCK_EX` sur fichier lock séparé — cross-process safe.
- Formule correcte : `api_port = 8080 + slot*100`, `web_port = 3000 + slot*100`, slot 0 réservé au main runtime.
- `_release_port_slot` appelé dans le bloc `finally` de `_do_sandbox` (ligne 579) — libération garantie en cas de succès, échec ou exception.

**Env file sandbox (plan §A)**
- `deploy.env` écrit avant le premier `_write_state` → ports visibles dès le début du run.
- Contient les 7 variables requises : `AI_DEV_FACTORY_RUNTIME_ROOT`, `AI_DEV_FACTORY_PROJECT_ROOT`, `AI_DEV_FACTORY_SUPERVISOR_PORT`, `API_PORT`, `WEB_PORT`, `COMPOSE_PROJECT_NAME`, `SANDBOX_ID`.

**docker-compose.yml (plan §B)**
- `"${API_PORT:-8080}:8080"` et `"${WEB_PORT:-3000}:80"` — main runtime non affecté.

**Schémas (plan §C–D)**
- `SandboxValidationState` et `SandboxValidationStatus` enrichis : `ports`, `worktree_path`, `compose_project` avec defaults backward-compatible.
- `_state_from_payload` dans `sandbox_runner.py` propage correctement les 3 champs.

**API runs (plan §E)**
- `runs_router` monté dans `main.py` ligne 120.
- `GET /sandbox-runs` : scan `sandboxes/*/state.json`, filtre par présence de `project_id` (exclut les SandboxManager entries).
- `GET /sandbox-runs/{id}/logs` : lecture directe du `run.log`, tail sur `lines` (borné 1–10000), retourne liste vide si absent.
- `DELETE /sandbox-runs/{id}` : validation regex → git worktree remove → fallback rmtree → release port registry → rmtree sandbox_dir. Scope strictement limité à `sandboxes/{sandbox_id}/`.

**Dashboard (plan §F–I)**
- `SandboxStatusPanel` : affiche `ports` (key-value) et `worktree_path`, bouton Refresh manuel.
- `SandboxRunsPanel` : 8 colonnes (ID, Project, State, Started, Finished, Last step, Ports, Worktree) + Actions.
- Auto-refresh 10s, LogsModal terminal dark, Cleanup désactivé pendant `running`/`pending`.
- `<SandboxRunsPanel />` rendu en bas de `DeployerPage`.

---

## Observations non bloquantes (inchangées)

**Race condition port registry** : `_release_port_slot_api` dans la route DELETE ne prend pas de file lock (contrairement au worker). Une libération simultanée runner/API reste théoriquement possible, très improbable en pratique (le runner libère à la fin du run, le cleanup UI est une action manuelle post-run).

**Locking sur fichier lock vide** : `open("r+")` sur un `touch()` vide est valide sur Linux/macOS (fcntl porte sur le fd, pas sur le contenu). Pas de risque pratique.

**SandboxRunsPanel** : polling 10s sans backoff ni circuit breaker — acceptable pour un outil interne.

**Pas de confirmation avant Cleanup** : le bouton est destructif sans dialogue de confirmation. Comportement acceptable pour l'audience interne mais à noter.

**`STATE_COLORS` dans `DeployerPage.jsx`** : l'état `pending` n'est pas dans la map de `SandboxStatusPanel` (ligne 112) mais le fallback `|| STATE_COLORS.idle` est présent — comportement fonctionnel, mineur.

---

## Conformité ticket

| Critère ticket | Statut |
|---|---|
| Ports sandbox isolés, non collision main runtime | ✓ |
| Deploy env file avec les 7 variables | ✓ |
| Compose project name unique par run | ✓ |
| Ports visibles dans UI et logs | ✓ |
| Historique des runs visible en UI | ✓ |
| Cleanup sécurisé (worktree + sandbox dir uniquement) | ✓ |
| Main runtime non affecté par le cleanup | ✓ |
| Validation sandbox existante toujours fonctionnelle | ✓ |

---

## Décision

Les deux problèmes bloquants sont corrigés. Le scope est respecté. L'implémentation est prête pour merge.

IMPLEMENTATION_APPROVED
