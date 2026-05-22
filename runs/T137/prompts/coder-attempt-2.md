# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T137 — T137 — Sandbox isolated ports and UI management

**Source**: GitHub Issue #123

## Description

Goal: improve sandbox deploy validation with isolated ports, sandbox env files, and dashboard management.

Context:
The sandbox runner now works host-side and executes scripts. The first real run failed because the sandbox reused the main runtime ports: supervisor 8090 and API 8080. The sandbox also needs its own deploy env file.

Scope:
- create a sandbox-specific deploy env file in each sandbox worktree
- include sandbox runtime root, project root, supervisor port, API port, web port, compose project name and sandbox id
- allocate ports that do not collide with the main runtime
- persist allocated ports in sandbox state
- run docker compose with a sandbox-specific project name
- list sandbox runs in the dashboard
- show sandbox id, project id, state, timestamps, last step, ports, worktree path and logs
- add refresh, view logs and cleanup actions
- cleanup removes only the selected sandbox worktree and sandbox directory
- cleanup must not affect the main runtime

Out of scope:
- AI fix loop
- tester agent
- cloud or remote deployment
- automatic merge

Acceptance:
- sandbox validation no longer conflicts with main ports
- every sandbox has its own env file
- every sandbox uses a unique compose project name
- ports are visible in UI and logs
- historical sandboxes are visible in UI
- cleanup works safely
- existing sandbox validation still works

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All clean. Here's a summary of all files created or modified:

---

## Changes made

### Created
- `apps/dashboard/src/components/SandboxRunsPanel.jsx` — new component listing all historical sandbox runs with Logs/Cleanup per row

### Modified

| File | What changed |
|---|---|
| `tools/agent_runner/run_sandbox.py` | Added `fcntl` import; `_allocate_port_slot`, `_release_port_slot`, `_write_sandbox_env` helpers; `_run_scripts` now accepts `extra_env`; `_do_sandbox` allocates ports, writes `deploy.env`, enriches state with `ports`/`worktree_path`/`compose_project`, and releases the slot in `finally` |
| `docker-compose.yml` | Port mappings now `${API_PORT:-8080}:8080` and `${WEB_PORT:-3000}:80` |
| `services/control_api/models/schemas.py` | Added `ports`, `worktree_path`, `compose_project` to both `SandboxValidationState` and `SandboxValidationStatus` |
| `services/control_api/services/sandbox_runner.py` | `_state_from_payload` now extracts and passes `ports`, `worktree_path`, `compose_project` |
| `services/control_api/routes/sandbox.py` | `get_project_sandbox_status` passes new fields; added `runs_router` with `GET /sandbox-runs`, `GET /sandbox-runs/{id}/logs`, `DELETE /sandbox-runs/{id}` |
| `services/control_api/main.py` | Mounts `sandbox.runs_router` |
| `apps/dashboard/src/api/deployer.js` | Added `listSandboxRuns`, `getSandboxRunLogs`, `cleanupSandboxRun` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | `SandboxStatusPanel` shows ports, worktree path and Refresh button; imports and renders `<SandboxRunsPanel />` |

---

## Review

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

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T137/reviews/implementation-review.md
- generated at: 2026-05-22T14:50:20Z

---

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