# Prompt Reviewer — T009

Rôle : Reviewer

Relire l’implémentation T009.

Vérifier :

- contexte de retry correctement reconstruit
- artefacts injectés explicitement logués
- erreurs claires si artefacts manquants
- aucune boucle automatique dangereuse
- `state.json` reste source de vérité
- `workflow-status.md` n’est pas utilisé pour décider
- README à jour

Produire une review structurée avec verdict :
- IMPLEMENTATION_APPROVED
- IMPLEMENTATION_FIX_REQUIRED
