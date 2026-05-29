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

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

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

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

The ticket follows.


# T164 — T164 - Replace Docker Compose v2.5-style environment networking with robust shared runtime network architecture

**Source**: GitHub Issue #179

## Description

# T164 - Replace Docker Compose v2.5-style environment networking with robust shared runtime network architecture

## Problem

The current dynamic Environment deployment/networking architecture behaves like an old Docker Compose v2.5-era setup:

- isolated per-compose default networks
- fragile dynamic network attachment
- Traefik not reliably attached to runtime networks
- service discovery instability
- broken dynamic route loading
- environment URLs failing despite containers running
- repeated runtime networking regressions

Observed symptoms:

- Traefik cannot resolve `api` / `web`
- environments start but URLs fail
- manual `docker network connect` debugging needed
- route/provider instability
- dynamic environment networking feels bolted-on instead of designed for multi-env runtime orchestration

Current state strongly suggests the architecture evolved from:

```text
single compose stack
```

instead of:

```text
multi-runtime environment orchestration platform
```

---

# Goal

Redesign Environment runtime networking around a proper shared runtime network architecture suitable for:

- multiple dynamic environments
- dynamic Traefik routing
- supervisor-managed runtimes
- reusable deploy pipelines
- runtime service discovery
- stable environment URLs

without relying on fragile compose-default isolated networks.

---

# High-level direction

Move from:

```text
one isolated compose network per environment
```

Toward:

```text
shared runtime ingress network
+ optional per-env internal networks
+ stable service discovery model
```

Traefik must always have deterministic access to runtime services.

---

# Required architecture audit

Audit current:

- compose generation
- network generation
- Traefik integration
- runtime service discovery
- route generation
- supervisor/runtime orchestration
- healthcheck assumptions
- deployer vs environments networking differences

Document:

- where networks are created
- who owns ingress networking
- how Traefik discovers services
- why dynamic env networking is unstable
- whether compose defaults are relied upon implicitly

---

# Desired target model

Example target architecture:

```text
shared ingress network
  ↕
Traefik
  ↕
environment services
```

Optional:

```text
shared ingress network
+ per-environment private network
```

But ingress connectivity must always be deterministic.

---

# Requirements

## Stable networking

Environment URLs must work immediately after successful deploy.

No manual:

```bash
docker network connect
```

must ever be required.

---

## Stable service discovery

Traefik must always be able to resolve backend services.

Avoid reliance on:

- compose-generated unstable network names
- accidental aliases
- timing-dependent attach behavior
- temporary dynamic network mutation

---

## Generic architecture

The solution must work for:

- multiple projects
- multiple environments
- concurrent runtimes
- custom sandbox paths
- future scaling of the runtime platform

Do NOT hardcode:

- one network name
- one project
- one compose stack

---

## Runtime ownership clarity

Clearly define ownership for:

- ingress network
- environment internal networks
- route generation
- Traefik registration
- runtime cleanup
- supervisor/runtime lifecycle

---

# Important constraints

Do NOT:

- patch around issues with repeated `docker network connect`
- hardcode network attachment everywhere
- bypass Traefik
- expose only host ports as primary architecture
- keep layering fixes on top of fragile compose-default networking

The goal is a proper runtime networking model.

---

# Suggested implementation directions

Potential approaches to evaluate:

- shared ingress network
- explicit external networks in compose generation
- deterministic network naming
- runtime network registry
- Traefik service discovery via labels instead of file-only routing
- supervisor-managed runtime attachment
- network lifecycle abstraction

---

# Tests

Add/validate:

## Multiple environments

Deploy multiple environments concurrently.

Assert:

- all URLs reachable
- no network conflicts
- Traefik reaches all envs

---

## Redeploy stability

Redeploy environments repeatedly.

Assert:

- routes remain valid
- no watcher/network races
- no orphaned networks

---

## Cleanup

Delete environment.

Assert:

- routes removed cleanly
- networks cleaned correctly
- other envs unaffected

---

# Acceptance criteria

- Dynamic environments work reliably through Traefik
- No manual network attach/debugging required
- Traefik consistently resolves environment services
- Networking architecture supports multiple concurrent environments
- Runtime networking ownership is clearly defined
- Compose-generated default-network fragility is eliminated
- Existing deployer/runtime flows continue functioning