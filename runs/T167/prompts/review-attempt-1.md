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


# T167 — T167 - Fix Traefik DNS/service discovery by enforcing shared ingress network for all routed containers

**Source**: GitHub Issue #186

## Description

# T167 - Fix Traefik DNS/service discovery by enforcing shared ingress network for all routed containers

## Problem

Traefik routes are registered successfully, but routed backends still fail with:

```text
proxy: route active (backend not healthy yet)
```

and runtime validation often shows:

```text
PASS proxy-infra ... http=502
FAIL api ... no response
FAIL web ... no response
```

Root cause is now strongly suspected to be incorrect Docker networking / service discovery architecture.

Specifically:

- Traefik and routed containers are not consistently attached to the same shared ingress network
- backend aliases may exist only on isolated compose-default networks
- Traefik cannot reliably resolve sandbox backend aliases through Docker DNS
- runtime networking behavior remains inconsistent across deployer/environments/redeploy flows

This is no longer a diagnostics problem.

This ticket must implement the actual networking fix.

---

# Goal

Make Traefik able to reliably resolve and reach every routed backend container through Docker DNS.

All routed containers must share a common ingress network with Traefik.

---

# Required architecture

## Shared ingress network

Introduce or finalize a single shared external Docker network:

```text
ai-dev-factory-runtime
```

This network is the canonical ingress network for:

- Traefik
- api containers
- web containers
- any future routed services

---

## Environment/service attachment

Every routed service must attach to BOTH:

```text
1. its local/default sandbox network
2. ai-dev-factory-runtime
```

Example:

```yaml
services:
  api:
    networks:
      default:
      ai-dev-factory-runtime:
        aliases:
          - sandbox-main-api

  web:
    networks:
      default:
      ai-dev-factory-runtime:
        aliases:
          - sandbox-main-web
```

---

## Traefik attachment

Traefik must also attach to:

```text
ai-dev-factory-runtime
```

and remain attached permanently.

---

## Stable DNS aliases

All backend aliases must be:

- lowercase
- Docker-safe
- deterministic
- derived from the canonical sandbox slug

Example:

```text
sandbox-main-api
sandbox-main-web
```

NOT:

```text
api
web
mixed-case aliases
```

---

# Required implementation work

## 1. Compose generation

Update compose generation so routed services join:

```text
ai-dev-factory-runtime
```

as an external network.

---

## 2. Traefik compose

Ensure Traefik compose permanently joins:

```text
ai-dev-factory-runtime
```

using:

```yaml
external: true
```

Do NOT let compose recreate/manage the runtime network.

---

## 3. Network ownership

`ensure_runtime_network()` becomes the ONLY owner/creator of:

```text
ai-dev-factory-runtime
```

No compose stack may create it independently.

---

## 4. Route backend targets

Generated route files must point to the shared-ingress aliases:

```text
http://sandbox-<slug>-api:8080
http://sandbox-<slug>-web:80
```

not host ports or isolated aliases.

---

## 5. Validation

During deploy validation, verify:

```bash
docker exec <traefik> wget http://sandbox-<slug>-api:8080/health
```

works successfully.

If not:

- fail deployment clearly
- log attached networks and aliases

---

# Important constraints

Do NOT:

- workaround via host.docker.internal
- rely on exposed host ports as primary architecture
- dynamically docker network connect/disconnect after startup as the main solution
- keep isolated compose-default-only networking
- hardcode one environment

The fix must support multiple concurrent environments cleanly.

---

# Acceptance criteria

- Traefik can resolve all backend aliases through Docker DNS
- `docker exec <traefik> wget http://sandbox-<slug>-api:8080/health` succeeds
- Routed environment URLs return real backend responses instead of 502
- Multiple environments work concurrently
- No manual docker network connect commands required
- Runtime ingress networking is deterministic and stable
- Existing deployer and environment flows continue to work

---

## Contexte de retry injecté par run_ticket.py

## Review decision keywords

The review must end with exactly one valid workflow keyword on its own line.

Approval keyword:
IMPLEMENTATION_APPROVED

Fix required keyword:
IMPLEMENTATION_FIX_REQUIRED
