# T012 — Enforce planner output contract

## Contexte

Pendant T010, plusieurs dérives planner ont été observées :

- le planner produit parfois un résumé au lieu d'un plan
- le planner peut produire une implémentation/changelog
- les retry planner ne réécrivent pas toujours un plan complet
- des sections importantes disparaissent entre les versions

Le workflow dépend d'un invariant critique :

Un planner doit toujours produire un plan canonique complet et autonome.

Aujourd'hui cet invariant n'est pas vérifié.

## Objectif

Ajouter une validation structurelle des outputs planner.

Le workflow doit pouvoir :
- détecter un faux plan
- détecter un résumé
- détecter une dérive coder/changelog
- empêcher les transitions invalides

## Inclus

### 1. Validator de plan

Ajouter un validateur dédié.

Le validateur doit vérifier :

- présence des sections obligatoires
- taille minimale raisonnable
- présence d'étapes d'implémentation
- présence des fichiers impactés
- présence des critères d'acceptation
- présence du hors scope

### 2. Détection des dérives planner

Refuser explicitement les outputs contenant des patterns de type :

- "implémentation terminée"
- "syntaxe valide"
- "changements appliqués"
- résumés de diff/changelog
- outputs trop courts

Le planner ne doit jamais agir comme un coder.

### 3. Retry planner canonique

Documenter et imposer :

- un retry planner doit produire un plan complet autonome
- jamais un delta
- jamais un résumé du précédent

### 4. Intégration workflow

Si validation échoue :
- log runtime explicite
- état inchangé
- erreur claire
- aucune transition vers PLAN_REVIEW_NEEDED

### 5. Observabilité

Ajouter dans runtime.log :

- planner validation success
- planner validation failure
- reason=...

## Hors scope

- validation sémantique complète du plan
- parsing AST markdown
- LLM judge
- multi-agent validation

## Critères d'acceptation

- un faux plan est rejeté
- un résumé est rejeté
- un changelog est rejeté
- un plan complet valide passe
- les retry planner restent complets
- aucune transition workflow invalide possible
