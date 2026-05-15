# Implementation fix 1 — T026

## Décision

IMPLEMENTATION_FIX_REQUIRED

## Problèmes à corriger

### P1 — Bloquant : polling infini post-merge

`handle_test_complete()` est appelé à chaque cycle du daemon pour tout ticket en `TEST_COMPLETE`, sans condition de sortie anticipée.

Après merge de la PR :
- `gh pr view`
- `gh issue close`
- `gh issue edit --remove-label`

peuvent être appelés à chaque cycle.

Fix attendu :
- persister `issue_closed: true` dans `state.json` après fermeture de l’issue
- vérifier ce flag au début de `check_and_close_issue()`
- ne pas rappeler GitHub si l’issue est déjà fermée
- ajouter tests dédiés

Amélioration recommandée :
- persister un flag ou un marqueur `pr_synced` / `pr_body_hash` pour éviter les `gh pr edit` répétés avec un body identique

### P2 — Mineur : gates PR incorrectes

`_pr_body()` affiche `PLAN_APPROVED` et `IMPLEMENTATION_APPROVED` non cochés alors qu’à `TEST_COMPLETE`, ces gates sont validées.

Fix attendu :
- cocher ces gates dans le body PR à `TEST_COMPLETE`
- ajouter ou adapter le test correspondant

## Contraintes

- pas de merge automatique
- pas de changement de scope
- conserver `run_ticket.py` comme moteur workflow
- conserver les tests existants verts
