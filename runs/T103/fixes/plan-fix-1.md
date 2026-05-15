PLAN_FIX_REQUIRED

Points à corriger :

1. `runs/.issue-intake.json` ne doit pas être ignoré sans décision explicite.
Ce fichier sert de registre issue→ticket et évite les réingestions.

2. Le plan doit aussi couvrir les checkpoints/push avant les gates humaines.
Le daemon doit checkpoint/push après :
- PLAN_REVIEW_NEEDED
- IMPLEMENTATION_REVIEW_NEEDED
- TEST_COMPLETE

avant arrêt ou création PR.

3. Le plan doit couvrir la synchronisation de la branche ticket avant toute étape agent.
Avant de relancer planner/coder/reviewer/tester sur un ticket existant, le daemon/worker doit garantir :
- checkout de la branche ticket attendue
- pull `--ff-only` de la branche distante
- abort sécurisé si conflit ou working tree dirty inconnu

Objectif : les fix artifacts, reviews ou commits ajoutés directement depuis GitHub doivent être visibles localement avant exécution de l’agent.
