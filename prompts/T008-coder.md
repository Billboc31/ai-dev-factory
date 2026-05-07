# Prompt Coder — T008

Rôle : Coder

Implémenter le mode `--auto` dans `run_ticket.py`.

Objectifs :
- exécuter automatiquement la prochaine étape
- afficher des logs visibles
- respecter les gates workflow
- supporter une boucle review/fix simple

Contraintes :
- rester explicite
- pas de merge automatique
- pas de PR automatique
- pas de boucle infinie

Contraintes obligatoires :
- ne jamais déduire l’état par recherche globale de chaînes dans workflow-status.md
- introduire un état canonique structuré, idéalement `runs/TXXX/state.json`
- définir une table de transitions autorisées
- imposer un budget max de boucles review/fix
- ne jamais marquer `IMPLEMENTATION_APPROVED` sans review + tester validés
- vérifier `git branch` + `git status` avant commit/push
- écrire des logs runtime dans `runs/TXXX/runtime.log`
- retourner un exit code non-zéro si un gate bloquant échoue
