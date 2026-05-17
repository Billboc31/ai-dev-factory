# T108 — T108 — Multi-project onboarding and project registry

**Source**: GitHub Issue #51

## Description

# T108 — Multi-project onboarding and project registry

## Objectif

Faire évoluer ai-dev-factory d’un orchestrateur mono-projet vers une plateforme multi-projets capable de :

- créer un nouveau projet géré
- bootstrapper un projet existant
- gérer plusieurs projets simultanément
- isoler agents/workers/configuration par projet
- préparer le futur issue tree / guardian multi-projets

---

## Vision

Architecture cible :

```text
ai-dev-factory
├── Project A
├── Project B
├── Project C
└── Global dashboard
```

Chaque projet possède :

- board
- daemon
- guardian
- issue mapper
- workers
- health status
- configuration projet
- ticket tree

---

## Nouveau projet

Ajouter un workflow :

```text
Create new project
```

Capable de :

- choisir un template
- créer structure repo
- initialiser Git
- générer `.ai-dev-factory/project.yml`
- créer premières issues
- démarrer daemon/guardian

---

## Bootstrap projet existant

Ajouter un workflow :

```text
Bootstrap existing repository
```

Capable de :

- connecter un repo existant
- analyser la stack
- détecter commandes build/test/run
- générer `.ai-dev-factory/project.yml`
- configurer guardian
- configurer issue mapper
- démarrer en mode observe

Le bootstrap doit être progressif :

```text
observe
→ planning
→ small fixes
→ feature delivery
```

---

## Project profile

Chaque projet doit posséder :

```text
.ai-dev-factory/project.yml
```

Décrivant :

- services
- checks
- smoke tests
- commandes build/test/run
- ports
- guardian config
- worker config

---

## SQLite registry

Ajouter une base SQLite locale servant de registre multi-projets.

Git/GitHub restent source de vérité pour :

- code
- issues
- PR
- artefacts runs/TXXX

SQLite sert pour :

- projects
- agents
- workers
- guardian runs
- project health
- issue tree snapshots
- dashboard state
- runtime metadata

---

## Dashboard

Ajouter :

```text
Projects page
```

avec :

- liste projets
- santé globale
- agents actifs
- workers actifs
- derniers incidents
- backlog résumé

Chaque projet doit avoir :

```text
Project board
```

isolé.

---

## Contraintes

- Git reste source de vérité workflow
- architecture multi-projets
- ne pas hardcoder ai-dev-factory
- compatible futurs worktrees/workers
- compatible guardian framework
- compatible future issue tree orchestration

---

## Critères d’acceptation

- un nouveau projet peut être créé via ai-dev-factory
- un repo existant peut être bootstrapé
- chaque projet possède son board isolé
- chaque projet possède ses agents/workers isolés
- SQLite maintient un registre multi-projets cohérent
- le dashboard affiche correctement plusieurs projets
