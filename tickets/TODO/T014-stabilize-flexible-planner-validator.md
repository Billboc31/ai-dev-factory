# T014 — Stabiliser le validator planner flexible

## Contexte

Le validator planner dans `tools/agent_runner/run_step.py` est une brique critique du workflow engine.

Le runner officiel `tools/agent_runner/run_ticket.py` importe directement `validate_planner_output` depuis `run_step.py` et l’utilise pendant les transitions automatiques quand l’étape courante est `planner`.

État actuel observé :

- `run_step.py` utilise déjà `import subprocess`
- `run_step.py` contient déjà `_REQUIRED_SECTION_GROUPS`
- `validate_planner_output()` valide déjà par groupes de synonymes
- `run_ticket.py` appelle déjà `validate_planner_output(output_content)` après une exécution planner

Le bug initial était que le planner ne passait jamais à cause d’une validation trop rigide des titres Markdown.

Un second bug vient d’être observé en runtime réel : le planner peut être rejeté parce qu’il mentionne une phrase interdite comme exemple de garde-fou, alors qu’il ne déclare pas avoir terminé une implémentation. Le validator doit donc distinguer une vraie revendication de fin d’implémentation d’une simple mention explicative dans un plan.

Avant, le système validait uniquement des sections exactes :

```text
## contexte
## objectif
## inclus
## hors scope
## critères d'acceptation
```

Problème : les LLM produisent souvent des variantes, synonymes, pluriels, formulations anglaises ou titres légèrement différents.

Résultat : des plans valides pouvaient être rejetés.

Le projet a déjà commencé à migrer vers une validation souple via `_REQUIRED_SECTION_GROUPS`, mais il faut vérifier que la migration est complète, renforcer les tests et confirmer le comportement en runtime réel.

## Objectif

Stabiliser définitivement la validation planner flexible.

Le validator doit :

- accepter des synonymes raisonnables de sections
- rester strict sur la structure minimale attendue
- continuer à détecter les faux plans
- éviter les faux positifs quand un plan mentionne des garde-fous de validation
- être couvert par des tests ciblés
- permettre au workflow de passer correctement de `INIT` à `PLAN_REVIEW_NEEDED`

## Inclus

### 1. Vérification du validator planner

Dans `tools/agent_runner/run_step.py`, vérifier :

- absence de l’ancien `import subprocessf`
- présence de `import subprocess`
- absence de dépendance active à une ancienne constante `_REQUIRED_SECTIONS`
- utilisation effective de `_REQUIRED_SECTION_GROUPS`
- validation par groupes de synonymes
- messages d’erreur explicites en cas de section manquante

### 2. Stabilisation des groupes de sections

Le validator doit reconnaître au minimum les groupes suivants :

- contexte
- objectif
- inclus
- hors scope
- critères d’acceptation

Chaque groupe peut accepter plusieurs variantes raisonnables.

Exemples de variantes acceptables :

```text
## contexte technique
## objectifs
## scope
## non inclus
## acceptance criteria
```

### 3. Conservation des garde-fous existants

Conserver les protections contre :

- plan trop court
- phrases de complétion interdites lorsqu’elles sont utilisées comme revendication réelle de fin de travail
- output déclarant que le code est déjà modifié
- output déclarant seulement que la syntaxe est correcte
- résumé déguisé d’implémentation

Le validator ne doit pas rejeter un plan uniquement parce qu’il décrit ces garde-fous comme règles à tester.

### 4. Tests ciblés

Ajouter ou mettre à jour des tests pour couvrir :

- un plan valide avec les titres canoniques
- un plan valide avec des synonymes
- un plan trop court
- un plan sans section obligatoire
- un output contenant une phrase interdite comme revendication réelle
- un plan valide mentionnant les garde-fous interdits comme objets de test

### 5. Test runtime minimal

Vérifier que le workflow peut exécuter l’étape planner et aboutir à :

```text
INIT
→ PLAN_REVIEW_NEEDED
```

Le test runtime peut être manuel si aucun framework d’intégration complet n’existe encore.

## Hors scope

- memory workflow
- GitHub Issues intake
- watcher local
- daemon permanent
- remote runners
- dashboard UI
- auto merge
- PR automation
- multi-agent orchestration
- replay tooling avancé
- refactor massif de `run_ticket.py`

## Critères d’acceptation

### Validator flexible

Un plan contenant des sections synonymes raisonnables est accepté.

Exemple :

```text
## contexte technique
## objectifs
## scope
## non inclus
## acceptance criteria
```

ne doit pas être rejeté uniquement à cause des titres.

### Validator strict sur le fond

Le validator continue à rejeter :

- les plans trop courts
- les plans sans groupe obligatoire
- les outputs déclarant que le travail est déjà fini
- les outputs contenant des phrases interdites comme revendications réelles

### Pas de faux positif sur les garde-fous

Un plan qui parle des phrases interdites comme règles de validation ou cas de test ne doit pas être rejeté uniquement pour cette mention.

### Tests présents

Des tests ciblés prouvent le comportement de `validate_planner_output()`.

### Workflow fonctionnel

Une exécution réelle ou simulée confirme que l’étape planner peut passer :

```text
INIT
→ PLAN_REVIEW_NEEDED
```

sans blocage dû au format exact des titres ni à une simple mention explicative des garde-fous.

### Aucun impact architecture

Le système reste :

- déterministe
- explicite
- reviewable
- Git-native
- sans merge automatique
- sans PR automatique
- sans autonomie implicite

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_step.py
tests/
prompts/T014-planner.md
```
