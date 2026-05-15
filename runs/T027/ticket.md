# T027 — T027 — Robust review decision parsing and fix artifact generation

**Source**: GitHub Issue #23

## Description

# T027 — Robust review decision parsing and fix artifact generation

## Contexte

Le workflow review fonctionne, mais deux irritants bloquent encore les fix loops en usage réel.

### Problème 1 — parsing review trop fragile

Aujourd’hui, `run_ticket.py` détecte une décision review seulement si le keyword est seul sur une ligne.

Mais les reviewers écrivent souvent :

```text
Verdict : IMPLEMENTATION_FIX_REQUIRED
Décision : IMPLEMENTATION_APPROVED
**IMPLEMENTATION_FIX_REQUIRED**
```

Résultat :

```text
warning: no review keyword found
state unchanged
```

alors que la review contient bien une décision claire.

### Problème 2 — fix artifact manquant

Quand une review demande un fix et que l’état passe à :

```text
PLAN_FIX_REQUIRED
IMPLEMENTATION_FIX_REQUIRED
```

le coder retry attend un artefact :

```text
runs/TXXX/fixes/plan-fix-N.md
runs/TXXX/fixes/implementation-fix-N.md
```

Mais cet artefact n’est pas toujours créé automatiquement.

Résultat :

```text
error: fix artifact missing
```

et l’utilisateur doit créer le fichier à la main.

## Objectif

Rendre les review decisions robustes et les fix loops automatiques.

Le workflow attendu :

```text
reviewer écrit IMPLEMENTATION_FIX_REQUIRED
→ run_ticket.py détecte la décision
→ state passe à IMPLEMENTATION_FIX_REQUIRED
→ fix artifact créé automatiquement depuis la review
→ coder retry peut démarrer sans intervention manuelle
```

## Inclus

### 1. Parsing review plus tolérant

Accepter les décisions review sous plusieurs formes :

```text
IMPLEMENTATION_APPROVED
IMPLEMENTATION_FIX_REQUIRED
PLAN_APPROVED
PLAN_FIX_REQUIRED

**IMPLEMENTATION_APPROVED**
**IMPLEMENTATION_FIX_REQUIRED**

Verdict : IMPLEMENTATION_FIX_REQUIRED
Decision: IMPLEMENTATION_APPROVED
Décision : PLAN_FIX_REQUIRED
```

Le parser doit rester strict sur les keywords autorisés par l’état courant.

### 2. Préserver les guardrails

Le parser ne doit jamais accepter un keyword hors `possible_next`.

Exemple :

```text
current_state=IMPLEMENTATION_REVIEW_NEEDED
possible_next=[IMPLEMENTATION_APPROVED, IMPLEMENTATION_FIX_REQUIRED]
```

Alors `PLAN_APPROVED` doit rester ignoré.

### 3. Génération automatique du fix artifact

Quand une décision `*_FIX_REQUIRED` est détectée, créer automatiquement le prochain fichier fix :

```text
runs/TXXX/fixes/plan-fix-1.md
runs/TXXX/fixes/implementation-fix-1.md
```

Le contenu doit inclure :

- la décision
- le chemin de la review source
- le contenu complet de la review
- un horodatage éventuel

### 4. Incrément correct

Si `implementation-fix-1.md` existe déjà, créer `implementation-fix-2.md`.

Même logique pour plan fixes.

### 5. Logs explicites

Ajouter des logs du type :

```text
auto-run: review keyword detected: IMPLEMENTATION_FIX_REQUIRED
auto-run: fix artifact written: runs/TXXX/fixes/implementation-fix-1.md
```

### 6. Tests

Ajouter des tests pour :

- keyword seul sur ligne
- keyword en gras Markdown
- `Verdict : KEYWORD`
- `Décision : KEYWORD`
- mauvais keyword ignoré
- fix artifact créé sur `PLAN_FIX_REQUIRED`
- fix artifact créé sur `IMPLEMENTATION_FIX_REQUIRED`
- incrément fix-N correct
- aucun fix artifact sur `*_APPROVED`

## Hors scope

- refactor complet du reviewer prompt
- changement du state machine
- daemon changes
- GitHub PR comments
- slash commands
- model routing

## Critères d’acceptation

- une review avec `Verdict : IMPLEMENTATION_FIX_REQUIRED` est parsée correctement
- une review avec `**IMPLEMENTATION_APPROVED**` est parsée correctement
- les keywords hors transition possible sont ignorés
- un fix artifact est créé automatiquement sur fix required
- le coder retry ne bloque plus avec `fix artifact missing`
- les logs sont explicites
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_ticket.py
tests/
README.md
```
