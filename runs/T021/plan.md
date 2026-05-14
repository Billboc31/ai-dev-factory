Le plan est écrit dans `runs/T021/plan.md`. Voici le résumé :

**Scope : 2 fichiers uniquement**

| Fichier | Action |
|---|---|
| `tools/agent_runner/run_ticket.py` | +1 constante `HUMAN_APPROVAL_TRANSITIONS`, +1 fonction `apply_human_approval`, +4 args CLI, dispatch dans `main` |
| `tests/test_human_approval.py` | nouveau — 9 cas ciblés |

**Logique centrale** — `apply_human_approval(ticket_id, command)` :
1. Lit l'état courant
2. Vérifie que l'état correspond à la précondition de la commande
3. Refuse (exit 2) si non
4. Applique la transition, logue, retourne 0

**Transitions codifiées** dans une table explicite `HUMAN_APPROVAL_TRANSITIONS` — aucune logique conditionnelle dispersée.

**Invariants préservés** : `--set-state` non modifié, aucun nouvel état workflow, aucune modification du daemon ou d'autres couches.
