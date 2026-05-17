# T105 — T105 — Automatic merge after TEST_COMPLETE

**Source**: GitHub Issue #47

## Description

# T105 — Automatic merge after TEST_COMPLETE

## Objectif

Permettre un merge automatique des PR ticket lorsque le workflow runtime atteint un état stable et validé.

Le merge automatique doit rester :

- sécurisé
- observable
- déterministe

---

## Contexte runtime récent

Après T104, les tickets peuvent être exécutés depuis des worktrees isolés.

Un bug a été observé avec T105 : les actions IHM sur un ticket appellent encore `run_ticket.py` depuis le repo principal sur `main`, ce qui provoque :

```text
commit-checkpoint: refused — current branch 'main' does not match state branch 'ticket/T105-...'
```

T105 doit donc aussi fiabiliser les actions dashboard sur tickets avant de finaliser l’auto-merge.

---

## Vision

Flux cible :

```text
planner
→ reviewer
→ tester
→ TEST_COMPLETE
→ checkpoint commit
→ push
→ PR create/update
→ automatic merge
```

Le pipeline ticket devient responsable jusqu’au merge.

Le guardian project agent surveillera ensuite la stabilité globale après merge.

---

## Dashboard ticket actions

Les actions IHM doivent résoudre correctement le contexte d’exécution du ticket.

Pour chaque action ticket :

```text
approve plan
request plan fix
approve implementation
request implementation fix
checkpoint
push
archive/finalize
```

le backend doit déterminer :

```text
ticket_id → active worktree cwd if present
else → safe legacy branch context
```

Règles :

- si un worktree existe pour le ticket, exécuter `run_ticket.py` avec `cwd=worktree`
- sinon, ne jamais exécuter une action ticket depuis `main` si `state.branch` attend une branche ticket
- soit checkout/sync explicitement la branche ticket avant action legacy
- soit refuser proprement avec un message actionnable
- les boutons IHM ne doivent plus produire `current branch main does not match state branch ...`

---

## Contraintes

Auto-merge uniquement si :

- reviewer validé
- tester validé
- working tree clean
- push OK
- branche ticket à jour avec main
- aucun conflit détecté
- aucun état ambigu runtime
- les actions IHM utilisent le bon cwd/worktree

---

## Travail demandé

- intégrer lifecycle merge dans le daemon
- ajouter logs explicites
- ajouter garde-fous sécurité
- intégrer statut merge dans dashboard
- vérifier synchro branche ticket avant merge
- vérifier état GitHub PR avant merge
- corriger les actions IHM ticket pour résoudre le bon cwd/worktree
- ajouter un test qui reproduit l’erreur `current branch main does not match state branch` et vérifie qu’elle n’arrive plus via l’IHM/backend

---

## Critères d’acceptation

- une PR est merge automatiquement après TEST_COMPLETE
- le merge respecte les garde-fous runtime
- le merge est observable dans logs et dashboard
- aucun merge si état ambigu ou dirty
- le merge produit un état runtime final propre
- les boutons IHM sur un ticket exécutent les actions dans le bon contexte worktree/branche
- aucune action IHM ticket ne tente un checkpoint/push depuis `main` si le ticket attend une branche ticket
