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

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

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

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

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

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T170 — T170 - Attach API/Web services to shared runtime network in environment compose flow

**Source**: GitHub Issue #192

## Description

# T170 - Attach API/Web services to shared runtime network in environment compose flow

## Problem

After fixing SANDBOX_ID propagation, routes now target the expected aliases:

```text
sandbox-d966c3e9f1c9-api
sandbox-d966c3e9f1c9-web
```

but Traefik still cannot resolve them:

```text
proxy: backend probe api=failed: wget: bad address 'sandbox-d966c3e9f1c9-api:8080'
proxy: backend probe web=failed: wget: bad address 'sandbox-d966c3e9f1c9-web:80'
```

Diagnostics show the actual remaining problem:

```text
traefik container networks=['ai-dev-factory-infra_default', 'ai-dev-factory-runtime']
api container networks=['sandbox-d966c3e9f1c9_default']
```

So Traefik is correctly attached to `ai-dev-factory-runtime`, but API/Web containers are not.

This means Docker DNS cannot resolve the routed aliases from the Traefik container.

---

# Goal

Ensure every routed service container (`api`, `web`) joins both:

```text
1. its sandbox default/internal network
2. ai-dev-factory-runtime shared ingress network
```

with the correct canonical aliases.

---

# Required fix

Update the compose generation / compose template used by the environment deploy flow so routed services are attached to the shared runtime network.

Expected rendered compose shape:

```yaml
services:
  api:
    networks:
      default: {}
      ai-dev-factory-runtime:
        aliases:
          - sandbox-${SANDBOX_ID}-api

  web:
    networks:
      default: {}
      ai-dev-factory-runtime:
        aliases:
          - sandbox-${SANDBOX_ID}-web

networks:
  ai-dev-factory-runtime:
    external: true
    name: ai-dev-factory-runtime
```

The aliases must use the same canonical SANDBOX_ID/slug used by route generation.

---

# Important distinction

This is NOT a SANDBOX_ID problem anymore.

SANDBOX_ID now appears correct in route generation.

The remaining failure is that containers are only attached to:

```text
sandbox-<id>_default
```

and not to:

```text
ai-dev-factory-runtime
```

---

# Validation commands

After fix, this must show both networks:

```bash
docker inspect <api-container> --format '{{json .NetworkSettings.Networks}}' | jq 'keys'
```

Expected:

```json
[
  "ai-dev-factory-runtime",
  "sandbox-<id>_default"
]
```

This must succeed:

```bash
docker exec <traefik-container> wget http://sandbox-<id>-api:8080/health
```

---

# Suggested files to audit

- docker-compose.yml
- compose generation code
- `.ai-dev-factory/scripts/start.sh`
- `services/control_api/services/sandbox_runtime_deploy.py`
- `services/control_api/services/sandbox_manager.py`
- any environment-specific compose template or runtime overlay

---

# Acceptance criteria

- API container is attached to `ai-dev-factory-runtime`
- Web container is attached to `ai-dev-factory-runtime`
- API/Web also keep their sandbox default/internal network
- Runtime aliases exist on `ai-dev-factory-runtime`
- Traefik resolves `sandbox-<id>-api` and `sandbox-<id>-web`
- `docker exec <traefik> wget http://sandbox-<id>-api:8080/health` returns HTTP 200
- Routed URLs no longer return 502 due to DNS/network failure
- Multiple environments can coexist without alias collisions