# AI Workflow — ai-dev-factory

## Objectif

Ce document définit le workflow officiel d’un ticket traité par ai-dev-factory.

Il sert de référence pour :
- les agents locaux
- les prompts IA
- les reviews automatiques
- les reviews manuelles ChatGPT
- la maintenance de la mémoire projet

## Principe central

Le repository est la source de vérité.

La conversation peut aider à créer, arbitrer ou reviewer, mais les décisions durables doivent être versionnées dans le repo.

## Lifecycle complet

1. Ticket creation
2. Risk classification
3. Planner
4. Plan review
5. Coder
6. Reviewer
7. Tester
8. Implementation review
9. Memory updater
10. Memory review
11. PR ready / merge

## Invariants obligatoires

Aucun code ne doit être écrit sans plan validé.

Aucune mémoire ne doit être mise à jour avant validation de l’implémentation.

Aucun merge ne doit être effectué sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Rôles

### Risk Classifier

Analyse le ticket et attribue un niveau de risque :
- AUTO_SAFE
- CHAT_REVIEW_REQUIRED
- HIGH_RISK

### Planner

Produit un plan court, concret et borné.

Le planner ne code pas.

### Plan Reviewer

Valide ou refuse le plan.

Objectifs :
- détecter dérive de scope
- détecter mauvaise architecture
- vérifier que le plan est exécutable
- vérifier que les risques sont identifiés

### Coder

Implémente uniquement après PLAN_APPROVED.

Le coder suit le plan validé et ne modifie pas la mémoire projet sauf instruction explicite.

### Reviewer

Produit une review technique de l’implémentation.

### Tester

Valide les critères d’acceptation avec des commandes ou vérifications reproductibles.

### Implementation Reviewer

Valide l’implémentation finale après coder, reviewer et tester.

### Memory Updater

Met à jour la mémoire projet uniquement après IMPLEMENTATION_APPROVED.

### Memory Reviewer

Valide que la mémoire reflète correctement le comportement réellement validé.

## Statuts de review

### Plan

- PLAN_APPROVED
- PLAN_FIX_REQUIRED

### Implémentation

- IMPLEMENTATION_APPROVED
- IMPLEMENTATION_FIX_REQUIRED

### Mémoire

- MEMORY_APPROVED
- MEMORY_FIX_REQUIRED

## Gestion des corrections

Quand une review refuse une étape, elle doit produire un fix prompt structuré.

Exemples :
- PLAN_FIX_REQUIRED → relancer Planner
- IMPLEMENTATION_FIX_REQUIRED → relancer Coder puis Reviewer/Tester
- MEMORY_FIX_REQUIRED → relancer Memory Updater

Les fix prompts doivent être stockés ou publiés comme artefacts versionnés ou commentaires PR.

## Niveaux de risque

### AUTO_SAFE

Ticket local, borné, faible risque architecture/sécurité/workflow.

Peut suivre le pipeline automatique complet.

### CHAT_REVIEW_REQUIRED

Ticket nécessitant une review conversationnelle ou manuelle.

Cas fréquents :
- changement architecture
- changement workflow IA
- changement mémoire globale
- refactor transversal
- changement de conventions

### HIGH_RISK

Ticket sensible ou potentiellement destructif.

Cas fréquents :
- suppression importante
- migration lourde
- sécurité sensible
- modification irréversible
- automatisation dangereuse

HIGH_RISK doit toujours être escaladé.

## Convention GitHub

GitHub sert de système nerveux du workflow.

Recommandations :
- 1 ticket = 1 branche = 1 PR
- la PR contient ou référence le ticket
- la PR contient les artefacts de plan/review/test/mémoire
- les statuts sont publiés en commentaire PR ou fichier workflow-status
- les corrections sont pilotées par fix prompts

## Mémoire projet

La mémoire projet est composée au minimum de :
- docs/ai/global-context.md
- docs/ai/project-life.md
- docs/ai/decisions-log.md

### global-context.md

Contexte stable, vision, invariants, règles durables.

Mise à jour rare.

### project-life.md

Journal vivant du projet : état actuel, tickets importants, décisions opérationnelles, dette connue.

Mise à jour fréquente.

### decisions-log.md

Décisions datées et justifiées.

Mise à jour à chaque décision structurante.

## Ordre mémoire obligatoire

La mémoire ne doit être mise à jour qu’après :
- ticket terminé techniquement
- review implémentation approuvée
- tests ou vérifications documentés

Ensuite seulement :
- Memory Updater modifie la mémoire
- Memory Reviewer valide
- PR peut être prête à merge

## Escalade vers conversation ChatGPT

Escalader vers une review chat si :
- le ticket modifie le workflow IA
- le ticket modifie la mémoire globale
- le ticket change l’architecture
- le ticket touche plusieurs composants
- le ticket introduit une automatisation autonome
- le ticket est ambigu ou stratégique

## Règle de fallback

Si un agent doute, il doit choisir l’option la plus sûre :
- ne pas élargir le scope
- demander review
- produire un fix prompt
- documenter l’incertitude
