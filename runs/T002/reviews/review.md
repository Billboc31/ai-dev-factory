# PR Review — T002 — `docs/ai/pr-lifecycle.md`

## Résumé

Le livrable `docs/ai/pr-lifecycle.md` couvre le ticket T002 : lifecycle PR IA générique, arborescence `runs/TXXX/`, statuts, séparation prompts canoniques / snapshots, responsabilités et escalade. Alignement correct avec `workflow.md` sans le dupliquer. **Décision : APPROVED** (améliorations mineures optionnelles ci-dessous).

## Vérifications effectuées

- Lecture de `tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md` (inclus / exclus / critères d’acceptation).
- Lecture intégrale de `docs/ai/pr-lifecycle.md`.
- Contrôle croisé avec `docs/ai/workflow.md` (statuts, gates, mémoire, escalade).
- Points de contrôle du prompt `T002-review.md` : branches, PR, artefacts, statuts, responsabilités, trois validations, escalade, GitHub comme source de vérité.

## Points validés

- **Branches et PR** : 1 ticket = 1 branche = 1 PR ; titres, description, checklist des trois `*_APPROVED` ; merge humain, pas de merge auto.
- **Artefacts standards** : arbre `runs/TXXX/` documenté (`plan.md`, `workflow-status.md`, `prompts/`, `reviews/`, `fixes/`, `tests/`, `memory/`) ; cohérent avec la structure type du ticket (étendue de façon utile avec plan et statut versionné).
- **Statuts workflow** : les six statuts reprennent `workflow.md` ; recommandation `workflow-status.md` + template ; distinction commentaire PR vs fichier versionné.
- **Responsabilités séparées** : agent local / conversation (exemple ChatGPT) / humain ; interdiction pour l’agent de modifier `prompts/` et de merger.
- **Trois validations obligatoires** : explicitement dans la checklist PR et dans les conditions de merge du tableau de transitions.
- **Escalade** : renvoi aux niveaux de risque et à la section escalade de `workflow.md` ; `HIGH_RISK` et fallback.
- **Générique** : pas de RAG, pas d’API, pas d’Actions, pas d’agent implémenté.
- **Prompts** : distinction claire `prompts/TXXX-*.md` (canoniques) vs `runs/TXXX/prompts/` (snapshots optionnels) ; règles anti double maintenance.
- **GitHub** : PR et historique comme système nerveux ; artefacts durables dans la branche — cohérent avec « GitHub = source de vérité workflow » du ticket.

## Problèmes détectés

Aucun **bloquant**.

**Améliorations mineures (optionnelles, hors exigence stricte du ticket)** :

1. **Étape « Risk classification »** : le tableau « Cycle étape par étape » résume surtout coder / mémoire / merge ; un futur agent pourrait bénéficier d’une ligne explicite du type « enregistrer le niveau de risque dans `workflow-status.md` (section Risk) dès la classification » — déjà partiellement couvert par le template de statut.
2. **Découverte du doc** : `workflow.md` n’a pas de lien vers `pr-lifecycle.md` (choix cohérent si l’on impose de ne pas toucher le workflow) ; la découverte repose sur `global-context.md` ou la navigation manuelle — acceptable.

## Risques éventuels

- **Lecture partielle** : un contributeur qui ne lit que `workflow.md` peut ignorer les détails `runs/` — mitigé par le lien dans `global-context.md` si maintenu.
- **Implémentation agent** : sans schéma minimal « ordre des fichiers créés au premier commit », des équipes pourraient initialiser `runs/` tard ; reste une question d’onboarding, pas une lacune du ticket.

## Décision

- **APPROVED**

## Actions demandées

- Aucune action bloquante avant merge fonctionnel du ticket T002.
- *(Optionnel)* : ajouter une phrase sur l’artefact ou la mise à jour du statut au moment de la classification risque, si on veut guider encore plus l’agent local minimal.
