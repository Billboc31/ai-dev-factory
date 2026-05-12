# T015 — Injecter dynamiquement les keywords de décision review

## Contexte

T014 a révélé un problème d’architecture dans le workflow de review.

Aujourd’hui, les prompts reviewer peuvent hardcoder des keywords comme :

```text
PLAN_APPROVED
PLAN_FIX_REQUIRED
```

Mais ces keywords ne sont valides que lorsque l’état courant est :

```text
PLAN_REVIEW_NEEDED
```

Quand l’état courant est :

```text
IMPLEMENTATION_REVIEW_NEEDED
```

le workflow engine attend au contraire :

```text
IMPLEMENTATION_APPROVED
IMPLEMENTATION_FIX_REQUIRED
```

Résultat observé pendant T014 : le reviewer a produit une review correcte sur le fond, mais avec un keyword incompatible avec l’état courant. `run_ticket.py` n’a donc pas pu parser la décision et a gardé l’état inchangé.

Ce problème ne doit pas être corrigé ticket par ticket dans les prompts métier.

Principe architectural voulu :

```text
Le workflow engine connaît les décisions attendues.
Les prompts reviewer restent génériques.
Le runtime injecte les keywords valides selon l’état courant.
```

Git reste la source de vérité workflow, et `state.json` reste la source de vérité d’état.

## Objectif

Faire de `run_ticket.py` la source de vérité des keywords de décision de review.

Le runner doit injecter dans le prompt runtime reviewer les keywords valides pour l’état courant.

Exemple pour une review de plan :

```text
Approval keyword: PLAN_APPROVED
Fix required keyword: PLAN_FIX_REQUIRED
```

Exemple pour une review d’implémentation :

```text
Approval keyword: IMPLEMENTATION_APPROVED
Fix required keyword: IMPLEMENTATION_FIX_REQUIRED
```

Le prompt reviewer ne doit plus hardcoder de keywords spécifiques à une étape.

## Inclus

### 1. Modéliser les décisions review

Dans `tools/agent_runner/run_ticket.py`, ajouter une structure explicite du type :

```python
REVIEW_DECISION_KEYWORDS = {
    "PLAN_REVIEW_NEEDED": {
        "approve": "PLAN_APPROVED",
        "fix": "PLAN_FIX_REQUIRED",
    },
    "IMPLEMENTATION_REVIEW_NEEDED": {
        "approve": "IMPLEMENTATION_APPROVED",
        "fix": "IMPLEMENTATION_FIX_REQUIRED",
    },
}
```

Cette structure doit rester cohérente avec `TRANSITIONS`.

### 2. Construire un contexte runtime review

Quand l’étape courante est `review`, `run_ticket.py` doit fournir à `run_step.py` un extra context contenant les keywords valides pour l’état courant.

Exemple de contenu injecté :

```markdown
## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
```

Ce contexte doit être écrit comme artefact dans `runs/TXXX/` pour rester reviewable.

Exemple possible :

```text
runs/TXXX/reviews/review-decision-context.md
```

ou un nom contextualisé équivalent.

### 3. Adapter l’appel review

`_call_run_step()` ou `auto_run()` doit injecter ce contexte uniquement pour les étapes `review`.

Attention : cette injection doit cohabiter avec l’injection existante des fix contexts.

### 4. Rendre les prompts reviewer génériques

Mettre à jour les prompts reviewer nécessaires, au minimum :

```text
prompts/T014-reviewer.md
```

et idéalement documenter la convention pour les futurs prompts reviewer.

Le prompt reviewer doit dire en substance :

```text
Utilise uniquement les keywords de décision fournis par le runtime.
Ne hardcode pas PLAN_APPROVED, PLAN_FIX_REQUIRED, IMPLEMENTATION_APPROVED ou IMPLEMENTATION_FIX_REQUIRED dans le prompt métier.
```

### 5. Tests

Ajouter ou mettre à jour des tests pour vérifier :

- les keywords injectés pour `PLAN_REVIEW_NEEDED`
- les keywords injectés pour `IMPLEMENTATION_REVIEW_NEEDED`
- aucun contexte review injecté pour les étapes non review
- `_determine_next_state()` continue à parser uniquement les keywords attendus par `TRANSITIONS`

## Hors scope

- risk classifier
- review externe/humaine automatique
- GitHub Issues intake
- watcher local
- daemon permanent
- merge automatique
- PR automatique
- memory workflow
- refactor massif de la state machine
- changement du format global de `state.json`

## Critères d’acceptation

### Keywords dynamiques

Pendant une review de plan, le prompt runtime contient :

```text
PLAN_APPROVED
PLAN_FIX_REQUIRED
```

Pendant une review d’implémentation, le prompt runtime contient :

```text
IMPLEMENTATION_APPROVED
IMPLEMENTATION_FIX_REQUIRED
```

### Prompts reviewer génériques

Les prompts reviewer ne hardcodent plus un couple de keywords spécifique à un état.

### Parsing inchangé

Le parsing de décision reste déterministe et basé sur les `possible_next` issus de `TRANSITIONS`.

### Artefacts reviewables

Le contexte de décision injecté est visible dans `runs/TXXX/` ou dans le snapshot runtime prompt quand celui-ci sera disponible.

### Pas d’autonomie implicite

Aucune décision n’est prise en dehors du keyword produit explicitement par le reviewer.

### Aucun impact dangereux

Le système reste :

- déterministe
- explicite
- reviewable
- Git-native
- sans merge automatique
- sans PR automatique
- sans agent caché

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_ticket.py
prompts/T014-reviewer.md
prompts/T015-planner.md
prompts/T015-coder.md
prompts/T015-reviewer.md
prompts/T015-tester.md
tests/
```
