J'ai tous les éléments. Voici la review complète.

---

## Review T007 — Git Ticket Branch Workflow

### Résumé

T007 corrige deux risques dans `run_ticket.py` (`checkout_branch`, `commit_ticket`) et crée `docs/ai/git-workflow.md`. La review précédente avait émis un `CHANGES_REQUESTED` sur trois points : la violation de convention de branche, le doublon dans `workflow-status.md`, et l'absence de justification pour le step 1 manuel. Les trois corrections ont été appliquées dans le commit `1a0087f`.

L'état courant : branche `ticket/T007-git-ticket-branch-workflow` existante, 1 commit d'avance sur `main`.

---

### Points validés

**Convention `ticket/TXXX-*` — branche créée**
- La branche `ticket/T007-git-ticket-branch-workflow` existe et correspond au format documenté.
- La review précédente signalait son absence ; elle est maintenant présente.

**`checkout_branch()` (run_ticket.py:87–93)**
- `git show-ref --verify --quiet refs/heads/{name}` → `checkout` ou `checkout -b` selon existence.
- Comportement non destructif, conforme au plan.

**`commit_ticket()` (run_ticket.py:96–109)**
- Staging limité à `runs/{ticket_id}/`.
- Note explicite à l'utilisateur pour les fichiers hors scope.
- Conforme au plan.

**`push_branch()` (run_ticket.py:112–115)**
- `git push -u origin <name>`, toujours explicite. Aucune automatisation cachée.

**Documentation `docs/ai/git-workflow.md`**
- Step 1 désormais explicitement annoté : *"étape manuelle — hors runner intentionnellement"* avec justification dans le paragraphe qui suit.
- 7 étapes complètes, invariants listés, commandes copiables.
- Liens vers `pr-lifecycle.md` et `workflow.md`.

**`workflow-status.md`**
- Doublon `## Last Update` supprimé. Un seul bloc final.

---

### Points à corriger

**[STRUCTUREL — non bloquant pour merge, à noter pour T008+]**

La branche `ticket/T007-git-ticket-branch-workflow` ne porte que les corrections de review (`1a0087f`). L'implémentation principale (`run_ticket.py`, `docs/ai/git-workflow.md`) est dans `086161c` sur `main`. Si une PR est ouverte depuis cette branche, elle ne contiendra que 3 fichiers de corrections, pas l'implémentation.

```
main:   ... ← 086161c (run_ticket.py + git-workflow.md) ← merge-base
branch:                                                  ← 1a0087f (review corrections)
```

C'est la limite inévitable d'une branche créée rétrospectivement après un commit sur `main`. Pas de rebase destructif justifié ici. Ce cas doit être documenté en post-mortem T007 : *"la branche rétroactive ne contient que les corrections de review, pas le corps du ticket — à éviter en T008+."*

Aucun autre point à corriger.

---

### Décision finale

**APPROVED**

Les deux corrections de code sont solides et non régressives. La documentation est claire, complète, et le step 1 est désormais justifié. Les trois points de la review précédente sont adressés. Le point structurel sur la branche rétroactive est connu, documenté, et sans alternative non destructive.

T007 peut être mergé. Le post-mortem sur la branche rétroactive est à intégrer dans la retrospective ou le CLAUDE.md pour guider T008+.
