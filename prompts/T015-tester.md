# Prompt Tester — T015

Rôle : Tester

Lis :
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T015-dynamic-review-decision-keywords.md
- runs/T015/plan.md
- runs/T015/implementation-output.md
- runs/T015/reviews/

## Objectif

Tester l’injection dynamique des review decision keywords.

## Tests attendus

### Review de plan

Vérifier qu’un review runtime pour :

```text
PLAN_REVIEW_NEEDED
```

reçoit :

```text
PLAN_APPROVED
PLAN_FIX_REQUIRED
```

### Review d’implémentation

Vérifier qu’un review runtime pour :

```text
IMPLEMENTATION_REVIEW_NEEDED
```

reçoit :

```text
IMPLEMENTATION_APPROVED
IMPLEMENTATION_FIX_REQUIRED
```

### Parsing workflow

Vérifier :

- parsing correct des keywords
- compatibilité `_determine_next_state()`
- compatibilité `TRANSITIONS`
- absence de parsing invalide

### Régression

Confirmer que :

- les fix loops fonctionnent encore
- les logs runtime existent toujours
- les étapes non-review ne reçoivent pas de review context
- aucune autonomie implicite n’a été introduite

## Sortie attendue

Produire :

- liste des tests exécutés
- résultats observés
- problèmes détectés
- verdict final sur l’injection dynamique des review decision keywords
