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

# Role — Planner

## Mission

Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.

## Tu dois

- comprendre le ticket
- proposer les étapes minimales
- lister les fichiers à créer ou modifier
- identifier les risques
- expliciter le hors scope
- produire un plan Markdown versionnable
- signaler les hypothèses nécessaires

## Tu ne dois pas

- coder
- réécrire le ticket
- anticiper les tickets suivants
- élargir le scope
- masquer les incertitudes

## Sortie attendue

Un fichier de plan conforme à `ai/templates/plan-template.md`.

## Règles

- le plan doit rester court
- le plan doit être exécutable par un Coder sans ambiguïté
- toute hypothèse doit être explicite
- toute dérive de scope doit être refusée

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

# SKILL: architecture-discipline

# Skill — Architecture Discipline

## Objectif

Préserver la cohérence architecture du projet dans le temps.

## Règles

- respecter les invariants documentés
- éviter les couplages implicites
- éviter les dépendances inutiles
- éviter les refactors transversaux non demandés
- documenter toute nouvelle règle structurante
- privilégier les changements locaux et bornés

## Refuser si

- le scope dérive
- plusieurs couches sont modifiées sans justification
- des conventions existantes sont cassées
- la mémoire projet devient incohérente

---

# SKILL: documentation

# Skill — Documentation

## Objectif

Maintenir une documentation utile, concise et alignée avec le code réel.

## Règles

- documenter les décisions importantes
- éviter les documentations vagues
- garder la mémoire projet cohérente
- expliciter les invariants architecture
- préférer Markdown simple et versionnable

## Refuser si

- la documentation diverge du comportement réel
- la mémoire contient des suppositions non validées
- des décisions importantes ne sont pas tracées

---

# TASK

# Generic Planner Task

Read the ticket below and produce a detailed implementation plan.

The plan must include:
- changes to implement (files, functions, logic)
- out-of-scope items
- risks and dependencies
- acceptance criteria

The ticket follows.


# T033 — T033 — Automatic workflow checkpoint commits after daemon/intake steps

**Source**: GitHub Issue #37

## Description

# T033 — Automatic workflow checkpoint commits after daemon/intake steps

## Contexte

Les tests runtime réels du daemon ont révélé un invariant manquant dans le workflow.

Aujourd’hui, le système peut :

```text
issue intake
→ création branche
→ création runs/TXXX
→ génération artefacts
→ changement state.json
```

mais certains fichiers restent non commités avant l’étape suivante.

Le daemon se bloque alors lui-même avec :

```text
error: working tree is not clean — commit or stash changes first
```

Les causes observées pendant T032 :

- `runs/T032/workflow-status.md`
- `runs/T032/daemon.lock`
- artefacts runtime générés entre deux cycles daemon

Le workflow doit devenir auto-stabilisant.

---

## Objectif

Introduire des checkpoint commits automatiques après les mutations workflow importantes.

Le daemon ne doit jamais tenter de lancer une étape auto-runnable avec un working tree dirty causé par ses propres artefacts.

---

## Invariant cible

Le workflow cible devient :

```text
step success
→ persist artefacts
→ checkpoint commit
→ push
→ next daemon cycle allowed
```

Et pour intake :

```text
GitHub issue
→ intake
→ create branch
→ create runs/TXXX
→ bootstrap checkpoint commit
→ push
→ workflow execution
```

---

## Travail demandé

### 1. Ajouter bootstrap checkpoint après intake

Après succès de `run_issue_intake.py`, le système doit automatiquement :

```text
commit bootstrap artefacts
push branch
```

Artefacts concernés typiquement :

```text
runs/.issue-intake.json
runs/TXXX/
```

Le commit doit utiliser le système canonique existant.

Ne jamais utiliser :

```bash
git add .
```

---

### 2. Ajouter checkpoint automatique après étapes workflow

Quand une étape réussit et produit des artefacts persistants :

- PLAN_REVIEW_NEEDED
- IMPLEMENTATION_REVIEW_NEEDED
- TEST_COMPLETE
- approvals humaines
- transitions importantes

le système doit automatiquement :

```text
checkpoint commit
push
```

avant le prochain cycle daemon.

---

### 3. Ignorer les fichiers runtime transitoires

Ajouter à `.gitignore` :

```gitignore
runs/daemon.log
runs/daemon.pid
runs/*/daemon.lock
runs/*/workflow-status.md
```

Ces fichiers runtime ne doivent jamais bloquer le workflow Git.

---

### 4. Garantir working tree clean avant exécution auto

Avant chaque lancement automatique de :

```bash
run_ticket.py TXXX --auto
```

le daemon doit garantir :

```text
working tree clean
```

Si le dirty state provient d’artefacts workflow persistants :

→ checkpoint commit automatique

Si le dirty state provient de fichiers inconnus/utilisateur :

→ abort sécurisé

---

### 5. Ajouter logs explicites

Ajouter des logs du type :

```text
checkpoint commit for T033
checkpoint push for T033
bootstrap checkpoint completed
```

et logs explicites si abort sécurité.

---

## Contraintes

- `run_ticket.py` reste le moteur workflow canonique
- aucune duplication Git dans le dashboard
- aucune modification directe arbitraire de `state.json`
- ne jamais utiliser `git add .`
- respecter `COMMIT_SCOPE`
- conserver les guardrails humains

---

## Critères d’acceptation

- un ticket intake peut être exécuté entièrement par le daemon sans intervention Git manuelle
- les étapes workflow ne laissent pas le repo dirty entre deux cycles
- les fichiers runtime transitoires ne polluent plus Git
- le daemon peut enchaîner plusieurs cycles sans blocage working tree
- les commits/push automatiques utilisent les scripts canoniques existants
- aucun `git add .`
- les logs runtime rendent les checkpoints observables