# T107 — T107 — Project guardian regression agent

**Source**: GitHub Issue #49

## Description

# T107 — Project guardian regression agent

## Objectif

Créer un agent global projet chargé de surveiller la santé du projet après merge.

L’agent tourne indépendamment des tickets runtime.

Il surveille principalement :

- branche main
- stabilité globale
- régressions
- qualité runtime

---

## Vision

Flux cible :

```text
Ticket runtime
→ TEST_COMPLETE
→ automatic merge
→ guardian project agent
→ full validation
→ regression issue if needed
```

Le guardian doit fonctionner comme un framework générique capable de tester n’importe quel projet décrit par une configuration projet.

---

## Architecture

Le guardian doit être composé de :

```text
guardian core
+ project profile
```

Le guardian core gère :

- sandbox / clone temporaire
- orchestration runtime
- lancement services
- exécution checks
- smoke tests
- collecte logs
- création issues régression
- cleanup environnement

Le projet décrit ses propres besoins via un fichier de configuration.

---

## Configuration projet

Ajouter un fichier du type :

```text
.ai-dev-factory/project.yml
```

Exemple :

```yaml
project:
  name: ai-dev-factory

services:
  - name: api
    command: uvicorn services.control_api.main:app --reload
    healthcheck: http://localhost:8000/health

  - name: dashboard
    command: npm run dev
    cwd: apps/dashboard
    healthcheck: http://localhost:5173

checks:
  - name: python tests
    command: pytest

  - name: frontend build
    command: npm run build
    cwd: apps/dashboard

smoke_tests:
  - name: dashboard board loads
    type: playwright
    script: tests/e2e/board.spec.ts
```

---

## Fonctionnement

Le guardian peut tourner :

- périodiquement
- après merge
- après push main

Workflow cible :

```text
clone sandbox
→ install deps
→ start services
→ wait healthchecks
→ run checks
→ run smoke tests
→ collect logs
→ create regression issue if needed
→ cleanup sandbox
```

---

## Smoke runtime tests

Le guardian doit pouvoir tester le runtime sans appeler de vrai LLM.

Exemple :

```text
→ create fake smoke issue
→ daemon intake
→ fake planner/coder/reviewer/tester
→ vérifier transitions runtime
→ vérifier dashboard
→ vérifier branches/runs
→ cleanup
```

Le système doit permettre des agents fake/mock pour réduire coût et temps de test.

---

## Régression

Si une régression est détectée :

```text
→ create GitHub issue
→ attach logs
→ mark severity
→ label ai-ready
```

---

## Dashboard

Ajouter une vue :

```text
Project Health
```

avec :

- dernier scan guardian
- état main
- build status
- dernières régressions
- tendance stabilité
- runtime incidents

---

## Contraintes

- Git reste source de vérité
- pas d’auto-revert dans cette V1
- pas d’auto-fix
- pas d’auto-merge obligatoire
- garder logs observables
- compatible multi-projets
- ne pas hardcoder ai-dev-factory dans le guardian core

---

## Critères d’acceptation

- le guardian peut tester la branche main indépendamment des tickets
- les régressions créent automatiquement des issues
- les logs de validation sont persistés
- le dashboard affiche la santé globale du projet
- le guardian peut fonctionner via un fichier project.yml spécifique au projet
