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


# T104 — T104 — Per-ticket worker worktrees and isolated runtime execution

**Source**: GitHub Issue #46

## Description

# T104 — Per-ticket worker worktrees and isolated runtime execution

## Contexte

Le modèle actuel exécute tous les tickets dans un seul clone Git local.

Même avec les améliorations T101/T102/T103, cette architecture provoque encore des problèmes structurels :

- conflit de branche courante
- dirty tree partagé
- checkpoint Git sensibles
- difficulté de parallélisation
- runtime fragile lorsqu’un ticket agit pendant qu’un autre est actif

Le problème principal est qu’un seul working tree Git est partagé entre plusieurs tickets.

---

## Vision cible

Transformer le daemon en architecture supervisor + workers isolés.

Le supervisor reste sur le repo principal et orchestre :

```text
issues
queue
capacity
board
worker lifecycle
```

Chaque ticket actif possède ensuite :

- son propre git worktree
- son propre cwd
- son propre runtime/logs/locks
- sa propre branche checkoutée

---

## Architecture cible

### Repo principal

```text
~/ai-dev-factory
```

Contient :

- supervisor daemon
- dashboard
- orchestration globale
- queue
- intake GitHub

---

### Worktrees ticket

```text
~/ai-dev-factory-worktrees/T104
~/ai-dev-factory-worktrees/T105
~/ai-dev-factory-worktrees/T106
```

Chaque worktree contient :

- branche ticket dédiée
- artefacts du ticket
- runtime isolé
- logs locaux du worker

---

## Objectif

Supprimer les conflits Git inter-ticket et préparer une vraie exécution parallèle contrôlée.

---

## Travail demandé

### 1. Créer un lifecycle worktree

Ajouter des helpers :

```text
create_ticket_worktree(ticket_id, branch)
remove_ticket_worktree(ticket_id)
get_ticket_worktree_path(ticket_id)
```

Utiliser :

```bash
git worktree add
```

Le worktree doit être créé automatiquement avant le lancement du worker.

---

### 2. Introduire la notion de worker ticket

Le supervisor daemon ne doit plus exécuter directement les étapes agent.

À la place :

```text
supervisor
→ lance worker T104
→ monitor worker
→ update board
```

Le worker exécute :

```text
planner
coder
reviewer
tester
```

uniquement dans son worktree.

---

### 3. Isoler les fichiers runtime

Chaque worker doit avoir :

```text
runs/T104/runtime.log
runs/T104/worker.pid
runs/T104/worker.lock
```

Le supervisor possède ses propres fichiers séparés.

---

### 4. Préparer la parallélisation future

Même si `max_active_workers=1` reste la valeur par défaut :

l’architecture doit permettre plus tard :

```text
T104 running
T105 waiting human
T106 running
```

sans conflit Git.

---

### 5. Intégrer au dashboard

Le dashboard doit afficher :

```text
Supervisor status
Workers list
Worker state
Worker branch
Worker cwd
Worker runtime status
```

Exemple :

```text
T104 — worker running planner
T105 — waiting human
T106 — queued
```

---

### 6. Gestion lifecycle worker

Définir clairement :

```text
worker start
worker stop
worker cleanup
worktree cleanup
worker crash handling
```

Ne jamais supprimer automatiquement un worktree contenant des changements non commités.

---

## Contraintes

- Git reste source de vérité
- pas de DB runtime dédiée
- pas de `git add .`
- pas d’auto-merge
- conserver les human gates
- supervisor et workers doivent être observables via logs
- éviter toute duplication de state machine

---

## Critères d’acceptation

- chaque ticket actif possède son propre worktree Git
- les tickets n’utilisent plus le même working tree local
- le supervisor n’exécute plus directement les étapes agent
- les logs/locks/runtime sont isolés par worker
- plus aucun conflit de branche courante entre tickets
- la board affiche les workers actifs
- l’architecture permet la parallélisation future

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation is committed. Here's a summary of what was built:

---

## T104 — Implementation Summary

### New file
- **`tools/agent_runner/worktree_manager.py`** — 3 helpers: `create_ticket_worktree`, `remove_ticket_worktree`, `get_ticket_worktree_path`. Uses `git worktree add/remove`. Refuses to auto-remove a worktree with uncommitted changes.

### Modified files (8)

**`tools/agent_runner/run_daemon.py`** (major):
- `DEFAULT_WORKTREES_DIR` = `~/ai-dev-factory-worktrees` (sibling of repo)
- `--worktrees-dir` and `--max-workers` CLI flags
- `_load/save/register/unregister_worker` for `runs/workers.json` registry
- `scan_tickets()` now scans worktrees first, falls back to main repo `runs/`
- `_get_run_dir()` resolves the correct run_dir (worktree takes priority)
- `launch_ticket()` split into two paths: worktree-based (CWD=worktree, no branch check) and legacy (existing behavior)
- `_sync_ticket_branch()` accepts optional `cwd=` for worktree context
- `_checkpoint_and_push_before_pr()` accepts optional `cwd=`
- `_commit_after_intake()` now commits `.issue-intake.json` directly to current branch (no longer via `run_ticket.py` which would fail after branch switch)
- `poll_github_issues()` creates the worktree immediately after intake
- `run_once()` threads `worktrees_dir` and `worktree_cwd` through all calls

**`tools/agent_runner/run_issue_intake.py`**: Records original branch, returns to it after bootstrap commit.

**`tools/agent_runner/run_ticket.py`**: `--repo-root` flag (forward-compatible); `checkout_branch()` is a no-op if already on the correct branch.

**`services/control_api/models/schemas.py`**: `BoardItem` gains `worker_pid` and `worker_cwd`.

**`services/control_api/services/board_service.py`**: Loads `workers.json`, prefers worktree state for active workers, marks tickets as Running if in workers registry, attaches `worker_pid`/`worker_cwd` to items.

**`apps/dashboard/src/pages/BoardPage.jsx`**: Running cards show `pid:XXXXX · T104` line.

**`apps/dashboard/src/pages/DaemonPage.jsx`**: New Workers panel listing active workers with branch, cwd, and pid.

---

## Review

La review est écrite. Voici le résumé :

---

## Résultat de la review — T104

**Décision : `IMPLEMENTATION_FIX_REQUIRED`**

### Bug bloquant identifié

Dans `run_issue_intake.py`, `commit_bootstrap` ne commite que `ticket.md` — `state.json` est écrit sur le filesystem mais jamais stagé. Quand le worktree est créé via `git worktree add`, il ne reçoit que les fichiers commités, donc `state.json` est absent du worktree.

Conséquence : à chaque cycle du daemon, `run_ticket.py --auto` lancé dans le worktree échoue immédiatement avec `"state not found"`. Le chemin worktree (le cœur du ticket) ne fonctionne jamais pour un ticket neuf.

**Correction requise** : ajouter `state.json` dans `commit_bootstrap` aux côtés de `ticket.md`.

### Autres problèmes détectés

- **Significatif** : après suppression manuelle d'un worktree, le repo principal montre le ticket à l'état `INIT` (stale), ce qui le re-queue indéfiniment.
- **Mineur** : `workers.json` stale après crash daemon (board incorrect).
- **Mineur** : `--max-workers > 1` accepté silencieusement mais non enforced.
- **Mineur** : nommage `daemon.lock` / `workers.json` diverge de la spec (`worker.lock` / `worker.pid`).

Le reste de l'implémentation est solide : la structure supervisor/worker, le backward compatibility, le dashboard, et la sécurité des suppressions de worktree sont corrects.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T104/reviews/implementation-review.md
- generated at: 2026-05-15T23:42:12Z

---

La review est écrite. Voici le résumé :

---

## Résultat de la review — T104

**Décision : `IMPLEMENTATION_FIX_REQUIRED`**

### Bug bloquant identifié

Dans `run_issue_intake.py`, `commit_bootstrap` ne commite que `ticket.md` — `state.json` est écrit sur le filesystem mais jamais stagé. Quand le worktree est créé via `git worktree add`, il ne reçoit que les fichiers commités, donc `state.json` est absent du worktree.

Conséquence : à chaque cycle du daemon, `run_ticket.py --auto` lancé dans le worktree échoue immédiatement avec `"state not found"`. Le chemin worktree (le cœur du ticket) ne fonctionne jamais pour un ticket neuf.

**Correction requise** : ajouter `state.json` dans `commit_bootstrap` aux côtés de `ticket.md`.

### Autres problèmes détectés

- **Significatif** : après suppression manuelle d'un worktree, le repo principal montre le ticket à l'état `INIT` (stale), ce qui le re-queue indéfiniment.
- **Mineur** : `workers.json` stale après crash daemon (board incorrect).
- **Mineur** : `--max-workers > 1` accepté silencieusement mais non enforced.
- **Mineur** : nommage `daemon.lock` / `workers.json` diverge de la spec (`worker.lock` / `worker.pid`).

Le reste de l'implémentation est solide : la structure supervisor/worker, le backward compatibility, le dashboard, et la sécurité des suppressions de worktree sont corrects.

IMPLEMENTATION_FIX_REQUIRED