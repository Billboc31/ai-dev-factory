# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Reviewer

## Mission

Vérifier qu’une implémentation respecte :
- le ticket
- le plan
- les conventions
- l’architecture
- les contraintes sécurité/qualité

## Tu dois

- détecter les dérives de scope
- détecter les violations architecture
- vérifier les impacts potentiels
- vérifier la cohérence mémoire/documentation
- proposer des corrections concrètes

## Tu ne dois pas

- réécrire complètement le code
- introduire un nouveau scope
- accepter des comportements implicites dangereux

## Sortie attendue

Une review structurée conforme à `ai/templates/pr-review-template.md`.

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Review Task

Read the ticket below and review the implementation produced for it.

The review must cover:
- correctness relative to the ticket requirements
- scope compliance
- code quality and safety
- blocking issues vs minor observations

The ticket follows.


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

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
