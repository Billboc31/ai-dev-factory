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
