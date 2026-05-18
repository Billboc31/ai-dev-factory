# T109 — T109 — Atomic runtime checkpoint and worktree-safe commit/push lifecycle

**Source**: GitHub Issue #54

## Description

# T109 — Atomic runtime checkpoint and worktree-safe commit/push lifecycle

## Contexte

Avant l’introduction des worktrees (T104), les transitions runtime fonctionnaient implicitement dans un seul repo/cwd.

Après T104/T105, plusieurs bugs sont apparus :

- état runtime modifié mais non commit/push
- dirty worktree après transition runtime
- commit/push exécuté depuis le mauvais cwd
- restart daemon refusé à cause d’un dirty tree
- transitions planner/coder/reviewer/tester non atomiques

Exemple observé :

```text
PLAN_APPROVED
→ implementation-output.md créé
→ state.json modifié
→ aucun commit/push final
→ daemon refuse relaunch : working tree is not clean
```

Le système a maintenant besoin d’une primitive unique et centralisée pour toutes les transitions runtime.

---

## Objectif

Créer un lifecycle de checkpoint runtime atomique et worktree-aware.

Toutes les transitions runtime doivent passer par la même primitive.

---

## Vision cible

Créer une abstraction centrale :

```python
checkpoint_transition(ticket_id, ...)
```

qui garantit toujours :

```text
1. resolve runtime cwd/worktree
2. git add runtime artifacts
3. commit checkpoint
4. push branche ticket
5. verify clean tree
6. fail loudly if persistence failed
```

---

## Runtime artifacts à gérer

Minimum :

```text
runs/TXXX/state.json
runs/TXXX/runtime.log
runs/TXXX/plan.md
runs/TXXX/review.md
runs/TXXX/test-report.md
runs/TXXX/implementation-output.md
runs/TXXX/*.json
```

Le système doit rester extensible.

---

## Travaux demandés

### 1. Nouveau module runtime checkpoint

Créer :

```text
tools/agent_runner/runtime_checkpoint.py
```

Fonctions proposées :

```python
resolve_ticket_cwd(ticket_id)
collect_runtime_artifacts(ticket_id)
checkpoint_transition(ticket_id, message, push=True)
verify_clean_tree(ticket_id)
```

---

### 2. Utilisation obligatoire partout

Toutes les transitions runtime doivent utiliser cette primitive :

- planner
- coder
- reviewer
- tester
- dashboard actions
- daemon transitions
- approve-plan
- request-fix
- TEST_COMPLETE
- auto-merge lifecycle

Aucun `git add/commit/push` ad-hoc ne doit rester.

---

### 3. Dirty tree safety

Le daemon doit pouvoir classifier :

```text
DIRTY_RUNTIME_CHECKPOINT
```

au lieu de juste :

```text
working tree is not clean
```

Le dashboard doit afficher explicitement :

- artifacts non persistés
- dernier commit runtime
- dernier push runtime
- fichiers dirty

---

### 4. Vérifications

Après checkpoint :

```text
git status --porcelain
```

must be empty.

Sinon :

- log erreur explicite
- état runtime FAILED ou BLOCKED_RUNTIME
- ne jamais continuer silencieusement

---

## Tests

Ajouter :

```text
tests/test_runtime_checkpoint.py
```

Cas minimum :

- checkpoint success
- push failure
- dirty tree remaining
- worktree cwd resolution
- ignored file handling (`git add -f`)
- concurrent ticket isolation

---

## Contraintes

- compatible legacy mode sans worktree
- compatible multi-worktree
- ne jamais commit sur `main`
- ne jamais masquer un push failure
- aucune transition runtime sans persistence Git validée

---

## Critères d’acceptation

- toutes les transitions runtime utilisent la même primitive
- plus aucun dirty tree après transition valide
- plus aucun commit/push oublié
- le daemon refuse proprement un runtime incohérent
- le dashboard expose clairement les erreurs de persistence runtime
- plusieurs tickets worktree peuvent tourner sans collision Git
