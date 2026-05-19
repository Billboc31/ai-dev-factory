# T115 — T115 — Package ai-dev-factory as installable Docker Compose runtime

**Source**: GitHub Issue #66

## Description

# T115 — Package ai-dev-factory as installable Docker Compose runtime

## Contexte

T113 et T114 ont validé une séparation majeure :

- clone humain
- clone runtime
- worktrees runtime
- runtime state
- orchestration daemon

Le framework ne doit plus tourner depuis le repository source développeur.

Le produit doit devenir un runtime installable et persistent.

---

# Objectif

Transformer ai-dev-factory en runtime installable via Docker Compose.

Le produit installé doit pouvoir :

- démarrer daemon/API/dashboard
- gérer plusieurs projets
- persister runtime state
- survivre aux upgrades
- fonctionner indépendamment du repo source développeur

---

# Architecture cible

## Produit installé

```text
container(s)
→ daemon
→ control-api
→ dashboard
```

## Runtime data persistante

```text
~/runtime/ai-dev-factory/
  state/
  logs/
  clones/
  worktrees/
  registry/
```

## Projets gérés

```text
managed projects
→ clones runtime isolés
→ worktrees agents
```

---

# Livrable cible

Démarrage via :

```bash
docker compose up -d
```

---

# Travail demandé

## Dockerisation

Créer :

- Dockerfile runtime
- docker-compose.yml
- volumes persistants runtime
- bootstrap runtime root

## Runtime root

Externaliser complètement :

- SQLite runtime
- logs
- clones
- worktrees
- registries
- runtime memory

hors du code applicatif.

## Configuration

Ajouter :

- runtime root configurable
- variables environnement
- support multi-instance
- support multi-project

## Runtime services

Conteneuriser :

- daemon
- control-api
- dashboard

## Git/runtime

Valider :

- aucun runtime state versionné
- aucun log versionné
- aucun pycache versionné
- aucun checkout dans clone humain

---

# Invariants attendus

- produit installé ≠ repo source
- runtime data persistante
- runtime redémarrable
- runtime remplaçable
- plusieurs runtimes possibles
- plusieurs projets gérés possibles
- worktrees runtime isolés

---

# Tests

Valider :

- docker compose up fonctionne
- restart container conserve runtime state
- upgrade image conserve runtime state
- plusieurs projets peuvent être gérés
- clone humain jamais modifié
- daemon fonctionne après restart
- worktrees runtime persistent

---

# Futur attendu après T115

Base pour :

- runtime registry
- memory system
- project registry
- multi-runtime orchestration
- distributed agents
- remote runtime deployment
- SaaS/self-host hybrid runtime
