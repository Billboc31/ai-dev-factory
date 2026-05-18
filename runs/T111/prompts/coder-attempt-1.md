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


# T111 — T111 — SQLite runtime state store for daemon, intake, workers and board

**Source**: GitHub Issue #58

## Description

# T111 — SQLite runtime state store for daemon, intake, workers and board

## Contexte

Le runtime actuel utilise trop Git et `runs/` comme base vivante :

- `runs/.issue-intake.json`
- `runs/workers.json`
- `runs/TXXX/state.json`
- locks
- retry state
- logs/runtime artifacts
- board state

Avec les worktrees, cela crée des problèmes récurrents :

- commits d’intake parasites sur `main`
- `main` local diverge de `origin/main`
- pull `--ff-only` impossible
- dashboard qui ne voit pas les tickets tant que les artefacts ne sont pas commit/push
- state Git local différent du state worktree
- workers invisibles ou fantômes
- dirty tree qui bloque le daemon
- intake qui pollue l’historique Git

Exemple observé :

```text
T109: intake — update issue index
```

commit créé localement sur `main`, sans valeur produit/code, bloquant ensuite `git pull --ff-only origin main`.

---

## Objectif

Introduire une base SQLite locale pour stocker l’état runtime vivant.

Git/GitHub restent source de vérité pour :

- code
- branches ticket
- PR
- issues GitHub
- artefacts auditables importants

SQLite devient source de vérité locale pour :

- intake
- état runtime courant
- workers
- locks
- retry/cooldown
- board
- transitions
- erreurs runtime
- health/status

---

## Principe d’architecture

Avant :

```text
Git + runs/ = code + runtime state + audit trail
```

Après :

```text
Git/GitHub = code + issues + PR + audit artifacts
SQLite = runtime state vivant
runs/ = artefacts/audit trail exportables, pas source runtime principale
```

---

## Données à migrer vers SQLite

### 1. Issue intake

Remplacer progressivement :

```text
runs/.issue-intake.json
```

par une table :

```sql
issue_intake(
  issue_number INTEGER PRIMARY KEY,
  ticket_id TEXT NOT NULL,
  branch TEXT,
  status TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_error TEXT
)
```

Objectif : ne plus committer l’index intake sur `main`.

---

### 2. Ticket runtime state

Ajouter :

```sql
ticket_runtime(
  ticket_id TEXT PRIMARY KEY,
  issue_number INTEGER,
  branch TEXT,
  state TEXT NOT NULL,
  run_dir TEXT,
  worktree_path TEXT,
  daemon_archived INTEGER DEFAULT 0,
  pr_number INTEGER,
  pr_state TEXT,
  last_transition TEXT,
  last_error TEXT,
  updated_at TEXT NOT NULL
)
```

Le `state.json` peut encore exister comme artefact, mais le daemon/board doivent lire SQLite en priorité.

---

### 3. Workers

Remplacer progressivement :

```text
runs/workers.json
```

par :

```sql
workers(
  ticket_id TEXT PRIMARY KEY,
  pid INTEGER,
  branch TEXT,
  worktree_path TEXT,
  status TEXT NOT NULL,
  started_at TEXT,
  heartbeat_at TEXT,
  updated_at TEXT NOT NULL
)
```

---

### 4. Locks

Ajouter :

```sql
runtime_locks(
  lock_name TEXT PRIMARY KEY,
  ticket_id TEXT,
  pid INTEGER,
  acquired_at TEXT NOT NULL,
  expires_at TEXT,
  metadata_json TEXT
)
```

Objectif : éviter les locks fichiers fragiles ou orphelins.

---

### 5. Retry / cooldown

Ajouter :

```sql
retry_state(
  ticket_id TEXT PRIMARY KEY,
  failure_class TEXT,
  retry_count INTEGER DEFAULT 0,
  cooldown_until TEXT,
  stopped INTEGER DEFAULT 0,
  stop_reason TEXT,
  updated_at TEXT NOT NULL
)
```

---

### 6. Runtime events / timeline

Ajouter :

```sql
runtime_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL
)
```

Le dashboard peut afficher la timeline depuis SQLite sans dépendre uniquement de `runtime.log`.

---

### 7. Project/board state minimal

Ajouter éventuellement :

```sql
runtime_metadata(
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

Pour stocker :

- dernier scan daemon
- version runtime
- dernier pull main
- health global
- préférences dashboard légères

---

## Travail demandé

### 1. Créer un module SQLite runtime

Créer :

```text
tools/agent_runner/runtime_db.py
```

Fonctions minimales :

```python
init_runtime_db(db_path)
record_issue_intake(...)
get_issue_intake(issue_number)
upsert_ticket_runtime(...)
get_ticket_runtime(ticket_id)
list_ticket_runtime()
upsert_worker(...)
remove_worker(ticket_id)
list_workers()
append_runtime_event(...)
```

---

### 2. Ajouter une migration/init automatique

Au démarrage du daemon/control-api :

```text
si DB absente → créer schéma
si DB présente → vérifier schéma version
```

Chemin par défaut proposé :

```text
.runtime/ai-dev-factory.sqlite
```

À gitignore :

```gitignore
.runtime/
*.sqlite
*.sqlite-wal
*.sqlite-shm
```

---

### 3. Modifier issue intake

Le daemon doit :

- vérifier l’intake dans SQLite
- ne plus dépendre uniquement de `.issue-intake.json`
- ne plus committer l’index intake sur `main`
- créer branche/worktree comme avant
- enregistrer le résultat dans SQLite

Pendant transition, `.issue-intake.json` peut rester en fallback lecture seule.

---

### 4. Modifier board/control-api

Le dashboard doit pouvoir lire :

- tickets runtime depuis SQLite
- workers depuis SQLite
- événements runtime depuis SQLite

Fallback temporaire autorisé :

```text
SQLite absent → lire runs/ legacy
```

---

### 5. Modifier workers registry

Le daemon doit écrire les workers dans SQLite.

`runs/workers.json` peut rester temporairement en export/debug, mais ne doit plus être la source primaire.

---

### 6. Modifier retry/cooldown

Migrer `retry-state.json` vers SQLite progressivement.

Fallback legacy accepté en V1.

---

### 7. Éviter tout commit runtime parasite sur main

Supprimer ou désactiver les commits automatiques de :

- `.issue-intake.json`
- `workers.json`
- locks
- retry state
- state runtime purement local

Les commits Git doivent rester réservés aux artefacts ticket auditables et aux modifications code.

---

## Contraintes

- Migration progressive, ne pas tout casser d’un coup
- Compatible tickets existants dans `runs/TXXX`
- Compatible worktrees existants
- Pas de dépendance externe autre que SQLite stdlib Python
- SQLite doit rester local et gitignored
- GitHub issues restent la source de vérité des demandes produit
- Git reste source de vérité code/PR

---

## Tests

Ajouter :

```text
tests/test_runtime_db.py
```

Cas minimum :

- init DB
- insert/update issue intake
- duplicate intake avoided
- ticket runtime upsert/list
- worker register/unregister
- runtime events append/list
- DB survives process restart

Ajouter aussi des tests daemon :

- intake issue uses SQLite instead of `.issue-intake.json`
- no commit on main for intake index
- board can list ticket from SQLite
- worker visible from SQLite

---

## Critères d’acceptation

- le daemon peut ingérer une issue sans créer de commit d’intake sur `main`
- `main` local ne diverge plus à cause de runtime state
- le board voit les tickets depuis SQLite
- les workers sont visibles depuis SQLite
- les tickets existants `runs/TXXX` restent lisibles en fallback
- `.issue-intake.json` n’est plus la source primaire
- `runs/workers.json` n’est plus la source primaire
- SQLite est gitignored
- tests runtime DB passent

---

## Hors scope V1

- multi-projets complet
- synchronisation cloud de la DB
- migration historique exhaustive de tous les anciens runs
- UI avancée d’administration DB
- suppression totale de `runs/`

---

## Pourquoi maintenant

T104/T105/T109 ont stabilisé les worktrees et checkpoints, mais ont aussi révélé que Git ne doit pas porter l’état vivant du daemon.

T111 doit stabiliser la base runtime avant de reprendre :

- T107 guardian
- T108 multi-project onboarding
- T110 UX/dashboard