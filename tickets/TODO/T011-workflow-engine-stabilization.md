# T011 — Workflow engine stabilization

## Contexte

T008 a introduit un moteur de workflow strict basé sur state.json.

T009 a ajouté les fix loops artifact-aware.

Pendant T010, plusieurs bugs runtime ont été découverts :
- keywords review non détectés
- mismatch review.md vs plan-review.md
- plans retry qui deviennent des résumés non canoniques
- confusion review humaine vs review agent
- transitions silencieuses difficiles à observer
- fix loops pas encore totalement fiables

## Objectif

Rendre le workflow engine T008/T009 fiable, observable et déterministe.

## Inclus

### 1. Naming unifié des reviews

- plan-review.md
- implementation-review.md
- plus jamais review.md générique

### 2. Détection robuste des keywords

Ajouter :
- log du fichier review parsé
- log du keyword détecté
- log explicite si aucun keyword trouvé
- fail clair si review invalide

### 3. Plans canoniques stricts

- un retry planner doit produire un plan complet autonome
- jamais un simple résumé delta

### 4. Ownership des reviews

Clarifier :
- review humaine
- review agent

Pas d’autonomie implicite.

### 5. Observabilité des transitions

Ajouter dans runtime.log des événements explicites :
- review parsed from: ...
- keyword detected: ...
- transition: ...

### 6. Fiabilité des fix loops

Valider réellement :
PLAN_FIX_REQUIRED
→ planner retry
→ PLAN_REVIEW_NEEDED

et équivalent implémentation.

## Hors scope

- pas de PR automatique
- pas de merge automatique
- pas de replay automatique
- pas de multi-agent
- pas de remote runner

## Critères d’acceptation

- plus aucune ambiguïté review filename
- les keywords workflow sont détectés de manière fiable
- les logs runtime permettent de comprendre les transitions
- les fix loops fonctionnent réellement de bout en bout
- les plans retry restent canoniques et complets
- distinction review humaine / review agent documentée
