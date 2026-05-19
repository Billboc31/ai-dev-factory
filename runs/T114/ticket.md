# T114 — T114 — Separate Human Clones from Runtime Clones and Isolate Managed Project Worktrees

**Source**: GitHub Issue #63

## Description

# T114 — Separate Human Clones from Runtime Clones and Isolate Managed Project Worktrees

## Contexte

T113 a révélé plusieurs limites structurelles importantes dans l’architecture actuelle :

* conflits Git/worktree
* branche `main` verrouillée par `_intake`
* pollution runtime (`runtime.log`, SQLite live DB, caches)
* friction entre développement humain et exécution agentique
* difficulté à maintenir un working tree propre
* framework et agents partageant le même clone Git

Le problème principal identifié est :

```text
Le clone Git utilisé par le développeur humain ne doit jamais être utilisé directement par les agents runtime.
```

L’architecture actuelle mélange :

* développement humain
* runtime daemon
* worktrees agents
* projets gérés

Ce couplage provoque :

* pollution Git
* conflits worktree
* état runtime fragile
* workflows difficiles à maintenir

---

## Objectif

Introduire une séparation stricte entre :

* clones humains
* clones runtime
* worktrees runtime
* projets gérés

afin de :

* protéger les workspaces humains
* isoler les agents
* éviter les conflits Git
* permettre plusieurs versions runtime
* préparer le multi-projets
* permettre rollback runtime
* rendre le daemon jetable/recréable

---

## Architecture cible

### Clone humain

Exemple :

```text
~/dev/ai-dev-factory
~/dev/doc-platform
```

Utilisé pour :

* développement humain
* architecture
* reviews
* expérimentation
* debugging manuel

Le daemon ne doit jamais tourner ici.

---

### Runtime root unique

```text
~/runtime/ai-dev-factory/
```

Ce dossier contient tout le runtime agentique.

---

### Clones runtime

```text
~/runtime/ai-dev-factory/clones/
```

Exemples :

```text
~/runtime/ai-dev-factory/clones/ai-dev-factory
~/runtime/ai-dev-factory/clones/doc-platform
~/runtime/ai-dev-factory/clones/rag-admin
```

Les agents travaillent uniquement dans ces clones runtime.

---

### Worktrees runtime

```text
~/runtime/ai-dev-factory/worktrees/
```

Organisation :

```text
~/runtime/ai-dev-factory/worktrees/<project>/<ticket>
```

Exemples :

```text
~/runtime/ai-dev-factory/worktrees/ai-dev-factory/T114
~/runtime/ai-dev-factory/worktrees/doc-platform/T041
```

Les worktrees ne doivent jamais être créés dans les clones humains.

---

### Runtime state

```text
~/runtime/ai-dev-factory/state/
```

Contient :

* SQLite runtime DB
* registries
* daemon state
* worker state

---

### Runtime logs

```text
~/runtime/ai-dev-factory/logs/
```

Contient :

* daemon logs
* runtime logs
* execution logs

Les logs ne doivent plus être versionnés dans Git.

---

## Inclus

* définir architecture runtime officielle
* définir séparation humain/runtime
* définir runtime root unique
* définir structure clones/worktrees/state/logs
* définir isolation projets gérés
* empêcher daemon sur clone humain
* définir règles Git/worktree
* définir invariants runtime
* préparer multi-version runtime
* préparer multi-instance runtime

---

## Exclus

* orchestration distribuée
* Kubernetes
* Dockerisation complète
* CI distante
* merge automatique
* memory system
* cloud orchestration

---

## Travail attendu

Créer ou mettre à jour :

```text
docs/ai/architecture.md
docs/ai/runtime-layout.md
docs/ai/workflow-invariants.md
```

Documenter :

* clone humain
* clone runtime
* runtime root
* worktrees runtime
* managed repositories
* runtime state
* runtime logs
* règles Git/worktree

Ajouter protections :

* refuser daemon sur clone humain
* détecter runtime root invalide
* empêcher création worktree hors runtime
* empêcher pollution runtime dans clones humains

---

## Invariants à formaliser

```text
Le daemon ne doit jamais tourner dans un clone humain.
```

```text
Les worktrees agents doivent être créés uniquement sous runtime/worktrees/.
```

```text
Les projets gérés doivent être isolés du framework.
```

```text
Les fichiers runtime ne doivent jamais polluer les clones humains.
```

```text
Une branche Git ne doit être checkoutée qu’une seule fois.
```

```text
Les logs runtime ne doivent jamais être versionnés.
```

---

## Critères d’acceptation

Le ticket est terminé si :

* architecture runtime documentée
* séparation humain/runtime claire
* runtime root défini
* structure clones/worktrees définie
* isolation projets gérés définie
* runtime DB/logs hors clones humains
* invariants documentés
* daemon protégé contre mauvais clone
* worktrees runtime isolés
* conflits Git/worktree réduits
* workflow développeur simplifié
