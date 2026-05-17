Le plan est écrit dans `runs/T105/plan.md`. Voici le plan complet mis à jour :

---

## Plan T105 — Automatic merge + runtime worktree-aware dashboard/actions

T105 doit corriger trois problèmes liés :

1. les actions IHM exécutées depuis le mauvais cwd (`main` au lieu du worktree ticket)
2. les lectures dashboard/runtime qui ne voient pas les tickets actifs dans un worktree
3. l’absence de merge automatique après `TEST_COMPLETE`

---

## Problème 1 — IHM cwd incorrect

### Symptôme

Les actions dashboard (`approve-plan`, `request-plan-fix`, `checkpoint`, `push`, etc.) appellent `run_ticket.py` depuis le repo principal, souvent sur `main`.

Cela provoque :

```text
commit-checkpoint: refused — current branch 'main' does not match state branch 'ticket/T105-...'
```

### Fix

Créer une résolution de cwd ticket-aware :

```text
ticket_id → worktree cwd si présent
sinon → repo principal en mode legacy sécurisé
```

### Fichiers concernés

- `services/control_api/services/subprocess_runner.py`
- `services/control_api/routes/tickets.py`
- `services/control_api/main.py`

### Règles

- Si un worktree existe pour le ticket, toute action IHM doit exécuter `run_ticket.py` avec `cwd=worktree`.
- Si aucun worktree n’existe, ne jamais exécuter une action ticket depuis `main` si `state.branch` attend une branche ticket.
- En fallback legacy : checkout/sync explicitement la branche ticket ou refuser proprement avec un message actionnable.

---

## Problème 2 — Dashboard/runtime invisibles avec worktrees

### Symptôme

Le daemon peut exécuter un ticket dans un worktree, mais certaines vues dashboard continuent à lire :

```text
runs/TXXX
```

dans le repo principal.

Conséquences :

- ticket invisible pendant exécution
- board qui ne voit pas l’état réel
- timeline incomplète
- logs/artifacts absents
- actions incohérentes

### Fix

Ajouter un resolver runtime partagé, utilisé partout.

Nouveau module proposé :

```text
services/control_api/services/runtime_resolver.py
```

Fonctions :

```python
resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir) -> Path
resolve_ticket_cwd(ticket_id, project_root, worktrees_dir) -> Path
```

### Règles de résolution

1. Lire le registry supervisor `runs/workers.json` si disponible.
2. Si le ticket a un `worktree_path` actif et que `worktree_path/runs/TXXX/state.json` existe : utiliser ce chemin.
3. Sinon vérifier `worktrees_dir/TXXX/runs/TXXX/state.json`.
4. Sinon fallback `project_root/runs/TXXX`.
5. Aucun accès direct à `runs/TXXX/...` ne doit rester dans les vues/actions runtime sans passer par le resolver.

### Fichiers à adapter

- `services/control_api/services/board_service.py`
- `services/control_api/services/artifact_reader.py`
- routes ticket detail / timeline / logs si présentes
- `services/control_api/services/subprocess_runner.py`
- `services/control_api/routes/tickets.py`

### Résultat attendu

Un ticket qui tourne entièrement dans un worktree doit être visible et pilotable dans l’IHM :

```text
Board → état réel
Ticket detail → timeline réelle
Logs → runtime.log réel
Actions → cwd réel
```

---

## Problème 3 — Pas de merge automatique

### Objectif

Après `TEST_COMPLETE`, le daemon doit finaliser automatiquement la PR si toutes les conditions sont réunies.

Flux cible :

```text
TEST_COMPLETE
→ checkpoint commit
→ push
→ create/update PR
→ verify PR state
→ merge PR automatically
→ delete branch if safe
→ mark runtime finalized
```

### Fix

Dans `tools/agent_runner/run_daemon.py`, ajouter :

```python
auto_merge_pr(ticket_id, run_dir, repo)
```

Garde-fous minimum :

- `pr_number` présent dans `state.json`
- PR existe
- PR state = OPEN
- pas de conflit détecté
- push/checkpoint OK
- état runtime non ambigu
- merge via `gh pr merge <number> --squash --delete-branch`

Si le merge échoue : log explicite, ne pas masquer l’erreur, ne pas marquer finalisé.

---

## Tests à ajouter ou adapter

### Nouveau test : `tests/test_ihm_worktree_cwd.py`

Vérifier que :

- une action dashboard sur ticket worktree utilise `cwd=worktree`
- l’erreur `current branch main does not match state branch` ne se produit plus
- fallback legacy refuse proprement ou checkout la bonne branche

### Nouveau test : `tests/test_runtime_resolver.py`

Cas à couvrir :

- worktree actif via `workers.json`
- worktree présent sans registry actif
- fallback repo principal
- state absent dans worktree → fallback propre

### Adapter : `tests/test_daemon_pr_lifecycle.py`

Cas pour `auto_merge_pr()` :

- succès
- PR déjà fermée/mergée
- PR conflictuelle
- `gh` absent
- merge command échoue

---

## Contraintes

- Git reste source de vérité workflow.
- Ne pas hardcoder T105.
- Ne pas casser le mode legacy sans worktree.
- Ne pas supprimer automatiquement un worktree dirty.
- Ne pas merger si état ambigu.
- Toutes les lectures/actions runtime doivent passer par le même resolver.

---

## Critères d’acceptation

- Les boutons IHM exécutent les actions dans le bon worktree/cwd.
- Aucune action IHM ticket ne tente un checkpoint/push depuis `main` si le ticket attend une branche ticket.
- Le board voit un ticket actif dans un worktree.
- La timeline/detail/logs/artifacts lisent les fichiers du worktree si actif.
- Une PR est merge automatiquement après `TEST_COMPLETE` lorsque les garde-fous sont OK.
- Les erreurs de merge sont visibles dans les logs et le dashboard.
- Les tests couvrent resolver, actions IHM et auto-merge.
