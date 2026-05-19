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

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All files parse cleanly. Here's a summary of what was implemented:

---

## Résumé des changements

### Fichiers modifiés (5)

| Fichier | Changement |
|---|---|
| `tools/agent_runner/runtime_db.py` | `get_db_path()` lit `AI_DEV_FACTORY_RUNTIME_ROOT` avant de faire `git rev-parse` |
| `tools/agent_runner/run_daemon.py` | `main()` dérive `runs_dir` et `worktrees_dir` depuis `RUNTIME_ROOT` si défini |
| `services/control_api/services/runtime_resolver.py` | Ajout de `resolve_runs_dir()` et `resolve_worktrees_dir()` respectant `RUNTIME_ROOT` |
| `services/control_api/services/artifact_reader.py` | `_runs_root()` délègue à `resolve_runs_dir()` |
| `services/control_api/main.py` | `create_app()` utilise `resolve_worktrees_dir()` pour le default |

### Nouveaux fichiers (6)

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image multi-stage : `dashboard` (build Vite) → `runtime` (Python + git + Claude CLI) → `web` (nginx) |
| `docker-compose.yml` | 3 services (`daemon`, `api`, `web`) + volume persistant `runtime-data` |
| `.dockerignore` | Exclut `.git`, `__pycache__`, runtime state, `node_modules` |
| `deploy/env.example` | Template — copier vers `deploy/.env` |
| `deploy/bootstrap.sh` | Crée la structure `RUNTIME_ROOT/runs`, `worktrees`, `clones`, etc. |
| `deploy/nginx.conf` | Sert le dashboard SPA + proxifie `/api/` vers le service `api` |

### Logique RUNTIME_ROOT

- Si `AI_DEV_FACTORY_RUNTIME_ROOT=/runtime` est défini :
  - DB SQLite → `/runtime/.runtime/ai-dev-factory.sqlite`
  - `runs_dir` → `/runtime/runs`
  - `worktrees_dir` → `/runtime/worktrees`
- Sans la variable → comportement local inchangé

### Limites connues

1. **Claude CLI auth** : le mount `~/.claude:/root/.claude:ro` dans `docker-compose.yml` suppose une auth déjà faite sur la machine hôte
2. **Git push depuis container** : nécessite le mount `~/.ssh` + `~/.gitconfig` (déjà dans compose)
3. **Dashboard API URL** : le dashboard doit être configuré pour appeler `/api/` (nginx proxy), selon le vite.config existant

---

## Review

---

## Review — T115 — Docker Compose runtime packaging

### Périmètre reviewé

Fichiers modifiés : `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/bootstrap.sh`, `deploy/env.example`, `deploy/nginx.conf`, `tools/agent_runner/run_daemon.py`, `tools/agent_runner/runtime_db.py`, `services/control_api/main.py`, `services/control_api/services/artifact_reader.py`, `services/control_api/services/runtime_resolver.py`.

---

### Conformité au plan approuvé

**BLOQUANT — Violation directe du plan approuvé (V1)**

Le plan approuvé contient une décision explicite et motivée :

> "Pour T115 V1, **ne pas installer Claude CLI dans l'image Docker**."
> "Le container ne doit pas embarquer de dépendance Claude obligatoire."
> "Le daemon peut rester lancé côté host dans T115 V1."

L'implémentation viole cette décision sur deux points :

**1. Claude CLI installé dans l'image Docker** (`Dockerfile`, lignes 17–23) :

```dockerfile
# Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    ...
# Claude CLI
RUN npm install -g @anthropic-ai/claude-code
```

**2. Service `daemon` conteneurisé** (`docker-compose.yml`, lignes 1–23) :

```yaml
daemon:
  ...
  command: >
    sh -c "
      /app/deploy/bootstrap.sh &&
      python tools/agent_runner/run_daemon.py
        --exec-cmd 'claude --dangerously-skip-permissions'
    "
```

Un service daemon dans Compose qui appelle `claude --dangerously-skip-permissions` n'est pas compatible avec V1 où Claude CLI reste côté host. Ce service ne peut pas fonctionner en état.

**Correction attendue** : retirer l'installation Node.js/Claude CLI du Dockerfile Stage 2. Retirer le service `daemon` de `docker-compose.yml`. Documenter (dans `env.example` ou commentaire) que le daemon doit être lancé côté host avec `RUNTIME_ROOT` pointant vers le même volume.

---

### Invariant ticket violé — pycache versionné

**BLOQUANT**

Le ticket stipule explicitement : "aucun pycache versionné".

Deux fichiers `.pyc` sont commités sur cette branche :

```
tools/agent_runner/__pycache__/run_step.cpython-314.pyc
tools/agent_runner/__pycache__/runtime_checkpoint.cpython-314.pyc
```

Ces fichiers doivent être supprimés de l'historique git (via `git rm --cached` + nouveau commit, ou rebase). Le `.dockerignore` les exclut correctement du contexte de build, mais ils restent dans le repository.

---

### Points corrects

- `runtime_db.py` : `get_db_path()` lit `AI_DEV_FACTORY_RUNTIME_ROOT` en priorité avant la résolution git — correct, conforme au plan.
- `run_daemon.py` : `main()` dérive `runs_dir` et `worktrees_dir` de `RUNTIME_ROOT` si défini — correct.
- `runtime_resolver.py` : même logique RUNTIME_ROOT dans l'API — correct.
- `bootstrap.sh` : idempotent (`mkdir -p`), crée toute la structure attendue dont `${RUNTIME_ROOT}/.runtime` pour SQLite.
- `.dockerignore` : exclut correctement `*.sqlite`, `.runtime/`, `__pycache__/`, `*.py[cod]`, `deploy/.env`, runtime state files.
- `docker-compose.yml` : volume nommé `runtime-data` monté sur `/runtime` — persistance correcte. SSH/gitconfig montés en `:ro` — correct.
- `nginx.conf` : proxy `/api/` → `http://api:8080/` avec suppression du préfixe — comportement SPA correct.
- `deploy/env.example` : documenté proprement, gitignored.

---

### Observations mineures (non-bloquantes)

**O1 — Runs/ artifacts dans l'image** : `.dockerignore` exclut `runs/*/state.json`, `runs/*/runtime.log` etc., mais laisse `runs/T*/ticket.md`, `runs/T*/plan.md` dans l'image. Ces artefacts workflow se retrouvent baked dans chaque build. Impact faible (lecture seule), mais peut surprendre.

**O2 — Bootstrap dupliqué** : les services `daemon` et `api` appellent tous deux `/app/deploy/bootstrap.sh`. Comportement idempotent donc sûr, mais si le service daemon est supprimé (comme demandé), ce point disparaît.

**O3 — env_file absent** : `docker-compose.yml` référence `deploy/.env` sans fallback. Si l'utilisateur n'a pas copié `env.example` → `.env`, le `docker compose up` échoue avec un message peu explicite. Un commentaire inline ou une note dans `env.example` guiderait mieux.

---

### Résumé

| Critère | Résultat |
|---|---|
| Conformité plan V1 | ❌ BLOQUANT — Claude CLI dans Docker + daemon conteneurisé |
| Invariant pycache | ❌ BLOQUANT — 2 fichiers `.pyc` commités |
| RUNTIME_ROOT path resolution | ✅ Correct |
| Volumes persistants | ✅ Correct |
| .dockerignore | ✅ Correct (hors .pyc déjà commités) |
| bootstrap.sh | ✅ Correct |
| nginx.conf | ✅ Correct |

Deux corrections bloquantes requises avant approbation :
1. Retirer Claude CLI + service daemon du Dockerfile/Compose (revenir à la décision V1 du plan)
2. Supprimer les fichiers `.pyc` commités

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T115/reviews/implementation-review.md
- generated at: 2026-05-19T12:49:56Z

---

---

## Review — T115 — Docker Compose runtime packaging

### Périmètre reviewé

Fichiers modifiés : `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/bootstrap.sh`, `deploy/env.example`, `deploy/nginx.conf`, `tools/agent_runner/run_daemon.py`, `tools/agent_runner/runtime_db.py`, `services/control_api/main.py`, `services/control_api/services/artifact_reader.py`, `services/control_api/services/runtime_resolver.py`.

---

### Conformité au plan approuvé

**BLOQUANT — Violation directe du plan approuvé (V1)**

Le plan approuvé contient une décision explicite et motivée :

> "Pour T115 V1, **ne pas installer Claude CLI dans l'image Docker**."
> "Le container ne doit pas embarquer de dépendance Claude obligatoire."
> "Le daemon peut rester lancé côté host dans T115 V1."

L'implémentation viole cette décision sur deux points :

**1. Claude CLI installé dans l'image Docker** (`Dockerfile`, lignes 17–23) :

```dockerfile
# Node.js for Claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    ...
# Claude CLI
RUN npm install -g @anthropic-ai/claude-code
```

**2. Service `daemon` conteneurisé** (`docker-compose.yml`, lignes 1–23) :

```yaml
daemon:
  ...
  command: >
    sh -c "
      /app/deploy/bootstrap.sh &&
      python tools/agent_runner/run_daemon.py
        --exec-cmd 'claude --dangerously-skip-permissions'
    "
```

Un service daemon dans Compose qui appelle `claude --dangerously-skip-permissions` n'est pas compatible avec V1 où Claude CLI reste côté host. Ce service ne peut pas fonctionner en état.

**Correction attendue** : retirer l'installation Node.js/Claude CLI du Dockerfile Stage 2. Retirer le service `daemon` de `docker-compose.yml`. Documenter (dans `env.example` ou commentaire) que le daemon doit être lancé côté host avec `RUNTIME_ROOT` pointant vers le même volume.

---

### Invariant ticket violé — pycache versionné

**BLOQUANT**

Le ticket stipule explicitement : "aucun pycache versionné".

Deux fichiers `.pyc` sont commités sur cette branche :

```
tools/agent_runner/__pycache__/run_step.cpython-314.pyc
tools/agent_runner/__pycache__/runtime_checkpoint.cpython-314.pyc
```

Ces fichiers doivent être supprimés de l'historique git (via `git rm --cached` + nouveau commit, ou rebase). Le `.dockerignore` les exclut correctement du contexte de build, mais ils restent dans le repository.

---

### Points corrects

- `runtime_db.py` : `get_db_path()` lit `AI_DEV_FACTORY_RUNTIME_ROOT` en priorité avant la résolution git — correct, conforme au plan.
- `run_daemon.py` : `main()` dérive `runs_dir` et `worktrees_dir` de `RUNTIME_ROOT` si défini — correct.
- `runtime_resolver.py` : même logique RUNTIME_ROOT dans l'API — correct.
- `bootstrap.sh` : idempotent (`mkdir -p`), crée toute la structure attendue dont `${RUNTIME_ROOT}/.runtime` pour SQLite.
- `.dockerignore` : exclut correctement `*.sqlite`, `.runtime/`, `__pycache__/`, `*.py[cod]`, `deploy/.env`, runtime state files.
- `docker-compose.yml` : volume nommé `runtime-data` monté sur `/runtime` — persistance correcte. SSH/gitconfig montés en `:ro` — correct.
- `nginx.conf` : proxy `/api/` → `http://api:8080/` avec suppression du préfixe — comportement SPA correct.
- `deploy/env.example` : documenté proprement, gitignored.

---

### Observations mineures (non-bloquantes)

**O1 — Runs/ artifacts dans l'image** : `.dockerignore` exclut `runs/*/state.json`, `runs/*/runtime.log` etc., mais laisse `runs/T*/ticket.md`, `runs/T*/plan.md` dans l'image. Ces artefacts workflow se retrouvent baked dans chaque build. Impact faible (lecture seule), mais peut surprendre.

**O2 — Bootstrap dupliqué** : les services `daemon` et `api` appellent tous deux `/app/deploy/bootstrap.sh`. Comportement idempotent donc sûr, mais si le service daemon est supprimé (comme demandé), ce point disparaît.

**O3 — env_file absent** : `docker-compose.yml` référence `deploy/.env` sans fallback. Si l'utilisateur n'a pas copié `env.example` → `.env`, le `docker compose up` échoue avec un message peu explicite. Un commentaire inline ou une note dans `env.example` guiderait mieux.

---

### Résumé

| Critère | Résultat |
|---|---|
| Conformité plan V1 | ❌ BLOQUANT — Claude CLI dans Docker + daemon conteneurisé |
| Invariant pycache | ❌ BLOQUANT — 2 fichiers `.pyc` commités |
| RUNTIME_ROOT path resolution | ✅ Correct |
| Volumes persistants | ✅ Correct |
| .dockerignore | ✅ Correct (hors .pyc déjà commités) |
| bootstrap.sh | ✅ Correct |
| nginx.conf | ✅ Correct |

Deux corrections bloquantes requises avant approbation :
1. Retirer Claude CLI + service daemon du Dockerfile/Compose (revenir à la décision V1 du plan)
2. Supprimer les fichiers `.pyc` commités

IMPLEMENTATION_FIX_REQUIRED