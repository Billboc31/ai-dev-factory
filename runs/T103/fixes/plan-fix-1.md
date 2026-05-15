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
