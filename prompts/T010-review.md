# Prompt Reviewer — T010

Rôle : Reviewer

Relire l’implémentation T010.

Vérifier :

- le snapshot contient exactement le prompt envoyé
- le snapshot est créé avant l’exécution du LLM
- les attempts sont correctement numérotées
- les fix loops T009 sont couverts
- les chemins sont loggés clairement
- aucune autonomie dangereuse ajoutée
- prompts canoniques inchangés
- README à jour

Produire une review structurée avec verdict :
- IMPLEMENTATION_APPROVED
- IMPLEMENTATION_FIX_REQUIRED
