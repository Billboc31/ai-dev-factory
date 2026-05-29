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

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 108 networking/proxy tests pass. Here is a summary of every file changed:

---

## Changes summary

### Infrastructure
| File | Change |
|------|--------|
| `deploy/infra/docker-compose.traefik.yml` | Declares + creates `ai-dev-factory-runtime` bridge network; connects Traefik service to it — Traefik now belongs to the shared ingress network permanently |
| `docker-compose.yml` | Declares `ai-dev-factory-runtime` as external; attaches `api` and `web` services to it with per-sandbox aliases `sandbox-${SANDBOX_ID:-default}-api` / `sandbox-${SANDBOX_ID:-default}-web` |

### Services
| File | Change |
|------|--------|
| `services/control_api/services/proxy_network.py` | **Rewritten**: removed `attach_traefik_to_compose_project`, `detach_traefik_from_compose_project`, `resolve_route_backends`, `host_port_backend_urls`, `compose_service_backend_urls`, `compose_default_network_name`, and all Docker subprocess helpers. Added `RUNTIME_NETWORK_NAME` constant and `sandbox_backend_urls(sandbox_id)` returning deterministic alias URLs |
| `services/control_api/services/proxy_manager.py` | Removed `compose_project` param from `register()` and `unregister()`; replaced `resolve_route_backends(ports, compose_project)` call with `sandbox_backend_urls(sandbox_id)`; removed `detach_traefik_from_compose_project` import and call |
| `services/control_api/services/infra_service_manager.py` | Added `ensure_runtime_network()` (idempotent `docker network create`); called from `_ensure_traefik_reverse_proxy()` so the ingress network is guaranteed before Traefik starts |
| `services/control_api/services/sandbox_manager.py` | Removed `compose_project=` kwarg from both `_proxy.register()` and `_proxy.unregister()` calls |
| `services/control_api/services/sandbox_runtime_deploy.py` | Removed `compose_project=` kwarg from `ProxyManager.register()` call |
| `tools/agent_runner/run_sandbox.py` | Removed `compose_project` param from `_register_proxy_route()` and its call site |

### Tests
| File | Change |
|------|--------|
| `tests/test_proxy_network.py` | **Rewritten**: 6 new tests for `RUNTIME_NETWORK_NAME` and `sandbox_backend_urls()` |
| `tests/test_proxy_manager.py` | Replaced port-content assertions with alias-URL assertions; removed `compose_project` args; renamed `test_register_custom_host_still_writes_port` → `test_register_custom_host_writes_alias_backends` |
| `tests/test_proxy_route_files.py` | Removed the mock for `attach_traefik_to_compose_project` and `compose_project` args; fixed alias-URL assertion in redeploy test |
| `tests/integration/test_multi_env_networking.py` | **New**: 5 tests — concurrent sandboxes have unique aliases, separate route files, no cross-contamination, no `host.docker.internal` |
| `tests/integration/test_redeploy_stability.py` | **New**: 4 tests — repeated register leaves single file with stable alias backend and no tmp files |
| `tests/integration/test_env_cleanup.py` | **New**: 4 tests — destroy one sandbox leaves other untouched, infra dashboard preserved, stale cleanup correct |

---

## Review

---

# PR Review — T164: Replace Docker Compose v2.5-style environment networking

## Résumé

The architecture change is correct and solves the root problem. However, two call sites were missed when removing the `compose_project` parameter from `ProxyManager.unregister()`, producing `TypeError` at runtime.

---

## Points validés

- `proxy_network.py` cleanly rewritten: `RUNTIME_NETWORK_NAME`, `sandbox_backend_urls()`, no `subprocess`/`docker network connect`.
- `proxy_manager.py:register()` correctly calls `sandbox_backend_urls(sandbox_id)`, no `compose_project`.
- `docker-compose.traefik.yml` connects Traefik to `ai-dev-factory-runtime`.
- `docker-compose.yml` declares `ai-dev-factory-runtime` as `external: true` with per-sandbox aliases using `${SANDBOX_ID:-default}`.
- Port alignment correct: API 8080, web 80 in both compose and `proxy_network.py`.
- `sandbox_manager.py:destroy()` (line 536) correctly calls `unregister()` without `compose_project`.
- `_dashboard.yml` protected from sandbox cleanup. `ensure_runtime_network()` idempotent.
- Integration tests for multi-env isolation, redeploy stability, and cleanup are thorough.

---

## Problèmes détectés

### [BLOCKING] B1 — `sandbox_runtime_deploy.py:389–393`

`ProxyManager.unregister()` called with `compose_project=state.compose_project` which no longer exists in the method signature. Raises `TypeError` uncaught in the deployment failure cleanup path, crashing `deploy_operational_runtime()` on any failed deployment after route registration.

**Fix:** Remove `compose_project=state.compose_project,` from lines 391.

### [BLOCKING] B2 — `run_sandbox.py:314–333` (`_unregister_proxy_route`)

Same stale kwarg: `compose_project=compose_project` passed to `ProxyManager.unregister()`. Caught by `try/except`, so no crash — but the route file is **never removed** on sandbox teardown, leaving stale subdomains pointing at recycled ports.

**Fix:** Remove `compose_project` parameter from `_unregister_proxy_route()` and from the `unregister()` call. Remove `compose_project=compose_project` from the call at `run_sandbox.py:1167`.

### [MINOR] M1 — `sandbox_runtime_deploy.py:284`

Stale docstring: "Attach Traefik to the compose network and write route file" — refers to the deleted `attach_traefik_to_compose_project()` pattern.

### [MINOR] M2 — Split network ownership

`ensure_runtime_network()` creates the network via `docker network create` before `TraefikManager().ensure_running()`, while `docker-compose.traefik.yml` also declares it as a compose-owned (non-external) network. Docker Compose v2 adopts pre-existing networks so this doesn't crash, but it's inconsistent with the plan's "Traefik compose as lifecycle owner" intent.

---

## Décision

The core architecture is sound. Two incomplete call-site cleanups (B1, B2) must be fixed before merge.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T164/reviews/implementation-review.md
- generated at: 2026-05-29T15:22:11Z

---

---

# PR Review — T164: Replace Docker Compose v2.5-style environment networking

## Résumé

The architecture change is correct and solves the root problem. However, two call sites were missed when removing the `compose_project` parameter from `ProxyManager.unregister()`, producing `TypeError` at runtime.

---

## Points validés

- `proxy_network.py` cleanly rewritten: `RUNTIME_NETWORK_NAME`, `sandbox_backend_urls()`, no `subprocess`/`docker network connect`.
- `proxy_manager.py:register()` correctly calls `sandbox_backend_urls(sandbox_id)`, no `compose_project`.
- `docker-compose.traefik.yml` connects Traefik to `ai-dev-factory-runtime`.
- `docker-compose.yml` declares `ai-dev-factory-runtime` as `external: true` with per-sandbox aliases using `${SANDBOX_ID:-default}`.
- Port alignment correct: API 8080, web 80 in both compose and `proxy_network.py`.
- `sandbox_manager.py:destroy()` (line 536) correctly calls `unregister()` without `compose_project`.
- `_dashboard.yml` protected from sandbox cleanup. `ensure_runtime_network()` idempotent.
- Integration tests for multi-env isolation, redeploy stability, and cleanup are thorough.

---

## Problèmes détectés

### [BLOCKING] B1 — `sandbox_runtime_deploy.py:389–393`

`ProxyManager.unregister()` called with `compose_project=state.compose_project` which no longer exists in the method signature. Raises `TypeError` uncaught in the deployment failure cleanup path, crashing `deploy_operational_runtime()` on any failed deployment after route registration.

**Fix:** Remove `compose_project=state.compose_project,` from lines 391.

### [BLOCKING] B2 — `run_sandbox.py:314–333` (`_unregister_proxy_route`)

Same stale kwarg: `compose_project=compose_project` passed to `ProxyManager.unregister()`. Caught by `try/except`, so no crash — but the route file is **never removed** on sandbox teardown, leaving stale subdomains pointing at recycled ports.

**Fix:** Remove `compose_project` parameter from `_unregister_proxy_route()` and from the `unregister()` call. Remove `compose_project=compose_project` from the call at `run_sandbox.py:1167`.

### [MINOR] M1 — `sandbox_runtime_deploy.py:284`

Stale docstring: "Attach Traefik to the compose network and write route file" — refers to the deleted `attach_traefik_to_compose_project()` pattern.

### [MINOR] M2 — Split network ownership

`ensure_runtime_network()` creates the network via `docker network create` before `TraefikManager().ensure_running()`, while `docker-compose.traefik.yml` also declares it as a compose-owned (non-external) network. Docker Compose v2 adopts pre-existing networks so this doesn't crash, but it's inconsistent with the plan's "Traefik compose as lifecycle owner" intent.

---

## Décision

The core architecture is sound. Two incomplete call-site cleanups (B1, B2) must be fixed before merge.

IMPLEMENTATION_FIX_REQUIRED