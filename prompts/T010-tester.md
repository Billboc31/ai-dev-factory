# Prompt Tester — T010

Rôle : Tester

Tester T010.

Scénarios minimum :

1. exécution simple sans contexte extra
2. exécution avec contexte injecté T009
3. plusieurs attempts du même step
4. vérifier que les snapshots sont distincts
5. vérifier que le contenu snapshot correspond exactement au prompt envoyé
6. vérifier que les chemins sont loggés
7. vérifier qu’aucune autonomie supplémentaire n’est introduite

Produire un rapport de test avec verdict :
- TEST_APPROVED
- TEST_FIX_REQUIRED
