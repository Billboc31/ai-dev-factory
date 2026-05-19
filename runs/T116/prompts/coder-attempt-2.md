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


# T116 — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

**Source**: GitHub Issue #68

## Description

# T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Contexte

T113/T114/T115 ont introduit :

* runtime root séparé du clone humain
* clones runtime
* worktrees runtime
* Docker Compose runtime
* API/dashboard containerisés
* daemon host-side

L’architecture fonctionne globalement mais plusieurs problèmes majeurs ont été découverts en runtime réel.

---

## Problèmes observés

### Runtime ownership ambigu

Plusieurs DB runtime concurrentes existent :

```text
.runtime/ai-dev-factory.sqlite
```

présentes :

* dans le clone humain
* dans les clones runtime
* dans les worktrees
* dans `_intake`

Cela provoque :

* board incohérent
* états divergents
* confusion runtime source-of-truth

---

### Runtime artifacts encore mélangés

Les éléments suivants continuent parfois à vivre dans les clones/worktrees :

* runs/
* logs/
* state/
* sqlite runtime
* daemon artifacts

Alors qu’ils doivent vivre uniquement dans :

```text
RUNTIME_ROOT/
```

---

### Worktrees runtime encore couplés au clone runtime

Les worktrees utilisent encore des données runtime locales.

Objectif :

* worktrees = jetables
* runtime = persistant

---

### Docker/runtime sync fragile

L’API Docker lit désormais correctement :

```text
/runtime/.runtime/ai-dev-factory.sqlite
```

mais :

* bootstrap migration absente
* hydratation runtime absente
* board fragile
* ownership non formalisé

---

## Objectif

Formaliser le runtime comme entité canonique indépendante du code source.

Le runtime devient :

```text
stateful
persistent
non-versioned
multi-instance capable
```

Le repo Git devient :

```text
product code only
```

---

# Architecture cible

## Runtime root canonique

```text
/runtime/<instance>/
```

Contient uniquement :

```text
.runtime/
runs/
logs/
state/
registry/
worktrees/
clones/
cache/
artifacts/
```

---

## Source de vérité runtime unique

UNE seule DB autorisée :

```text
/runtime/<instance>/.runtime/ai-dev-factory.sqlite
```

Interdictions :

* aucune DB dans worktree
* aucune DB dans clone
* aucune DB dans repo humain

---

## Worktrees jetables

Les worktrees :

* ne stockent aucun état persistant
* ne possèdent aucune DB
* ne possèdent aucun logs runtime
* peuvent être détruits/recréés à volonté

---

## Runtime-aware services

Tous les composants doivent résoudre leurs paths via :

```text
AI_DEV_FACTORY_RUNTIME_ROOT
```

Plus aucun fallback implicite vers :

```text
/app
repo root
cwd
```

---

## Préparation multi-runtime

Préparer le terrain pour :

```text
runtime-dev
runtime-prod
runtime-client-x
runtime-doc-platform
```

avec :

* isolation complète
* DB dédiée
* logs dédiés
* worktrees dédiés
* ports dédiés
* registry dédiée

---

## Livrables

* runtime ownership spec
* migration bootstrap runtime
* suppression DB locales worktrees/clones
* cleanup runtime artifacts
* runtime hydration au démarrage Docker
* board stable après restart
* invariant checks runtime
* documentation architecture runtime

---

## Contraintes

* aucun retour au modèle “repo = runtime”
* compatibilité daemon host-side conservée
* Docker API/dashboard doivent fonctionner
* worktrees existants ne doivent pas être cassés brutalement
* migration progressive acceptable

---

## Future work (hors scope)

* daemon containerisé
* runtime manager UI
* runtime create/start/stop
* runtime registry global
* distributed runtimes
* remote workers

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All changes are in scope. Here's a summary of what was implemented across the 8 plan steps:

---

**Files modified:**

| File | Change |
|------|--------|
| `services/control_api/services/board_service.py` | Step 1: `_load_runtime_db` now reads DB from `RUNTIME_ROOT/.runtime/` when env var is set. Step 5: `get_board` computes `state_dir` and uses it for JSON fallback of workers/issue-index. |
| `tools/agent_runner/runtime_db.py` | Step 2: Removed `subprocess` import and the `git rev-parse --git-common-dir` call. Dev fallback now uses `Path(__file__).resolve().parent.parent.parent` (stable, CWD-independent). |
| `tools/agent_runner/run_daemon.py` | Step 3: `state_dir` threaded through `launch_ticket`, `run_once`, `poll_github_issues`; workers.json and .issue-intake.json now read/written from `state_dir`. Step 4: `_LOG_FILE` module variable + `_log()` writes to `RUNTIME_ROOT/logs/daemon.log` when set. |
| `services/control_api/services/runtime_resolver.py` | Step 6: Added `resolve_state_dir()` and `resolve_logs_dir()`. |
| `deploy/bootstrap.sh` | Step 7: Best-effort migration of SQLite DB, `workers.json`, and `.issue-intake.json` from old locations to canonical ones. Never overwrites existing files. |
| `docs/ai/runtime-layout.md` | Step 8: Updated "état réel" section to reflect T116 changes and residual gaps. |
| `docs/ai/decisions-log.md` | Step 8: New T116 entry documenting the structural decisions. |

**Key invariant preserved:** all changes fall back gracefully when `AI_DEV_FACTORY_RUNTIME_ROOT` is not set — dev-without-Docker keeps working as before.

---

## Review

I have all the information I need. Let me write the review.

---

# Review — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Résumé exécutif

L'implémentation corrige les problèmes critiques en production (board DB path, workers registry, daemon logging) et maintient la compatibilité descendante. Elle est correcte pour le cas Docker/production. Trois défauts structurels nécessitent des corrections avant approbation.

---

## Scope compliance

L'implémentation est bornée au ticket. Pas de dérive de scope observée. Le plan approuvé est intégralement implémenté.

Les livrables couverts :
- ✅ Runtime ownership spec (décisions-log.md, runtime-layout.md)
- ✅ Migration bootstrap runtime (deploy/bootstrap.sh)
- ✅ Séparation state_dir / runs_dir
- ✅ Board stable après restart (board_service.py)
- ✅ File logging daemon vers RUNTIME_ROOT/logs/daemon.log
- ⚠️ Invariant checks runtime — **livrable explicite du ticket, absent**
- ⚠️ Suppression DB locales — migration uniquement, pas de cleanup (acceptable per contrainte "migration progressive")

---

## Problème #1 — BLOQUANT : `resolve_state_dir()` / `resolve_logs_dir()` sont du dead code

**Fichier :** `services/control_api/services/runtime_resolver.py:28-41`

Les deux fonctions ajoutées à l'étape 6 du plan ne sont jamais importées ni appelées. `board_service.py` et `run_daemon.py` dupliquent la logique de résolution en ligne chacun de leur côté :

```python
# board_service.py — inline, non extrait
runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
if runtime_root:
    db_path = Path(runtime_root) / ".runtime" / "ai-dev-factory.sqlite"

# run_daemon.py — inline, non extrait
if runtime_root:
    rt = Path(runtime_root)
    state_dir = rt / "state"
```

Résultat : l'abstraction "canonical resolver" existe mais n'est pas utilisée. Si le nom de l'env var change ou si la logique de résolution évolue, elle devra être corrigée à 3 endroits au lieu d'un.

**Correction attendue :** soit utiliser `resolve_state_dir()` dans `board_service.py` et `run_daemon.py`, soit supprimer ces helpers s'ils ne sont pas encore prêts à être intégrés.

---

## Problème #2 — BLOQUANT : `runtime_db.py` — le nouveau fallback crée des DB dans les worktrees

**Fichier :** `tools/agent_runner/runtime_db.py:80-83`

```python
# Dev fallback: this module lives at tools/agent_runner/runtime_db.py,
# so parent.parent.parent resolves to the repo root deterministically.
return Path(__file__).resolve().parent.parent.parent / _DB_FILENAME
```

Ce raisonnement est faux pour les processus workers. Quand `run_ticket.py` est exécuté depuis un worktree, Python charge `runtime_db.py` depuis la copie locale du worktree. `Path(__file__).resolve()` retourne alors `<worktree>/tools/agent_runner/runtime_db.py`, et `.parent.parent.parent` est la racine du worktree — pas le repo principal.

L'**ancien comportement** via `git rev-parse --git-common-dir` renvoyait toujours le common git dir (celui du clone principal), garantissant que tous les processus — y compris ceux lancés depuis des worktrees — partageaient **une seule DB**. Le nouveau fallback brise cette propriété en dev mode.

En Docker (RUNTIME_ROOT set), ce chemin n'est jamais atteint — le bug est donc invisible en production. Mais en dev local, il peut recréer exactement le problème décrit dans le ticket : DB fragmentées par worktree.

Le docstring du module (ligne 5-6) dit encore "resolved from the git common dir so all worktrees share one DB" — il est désormais incorrect.

**Correction attendue :** rétablir le fallback `git common-dir` (supprimer le subprocess uniquement si RUNTIME_ROOT est set, et conserver git common-dir en fallback dev), ou imposer explicitement RUNTIME_ROOT en dev (avec une erreur claire), ou conserver le fallback module-location **uniquement** en documentant qu'il est réservé à des invocations depuis le clone principal.

---

## Problème #3 — MOYEN : Invariant checks absents (livrable explicite du ticket)

Le ticket liste explicitement `invariant checks runtime` comme livrable. Aucun check n'est présent dans l'implémentation.

Un check minimal acceptable serait un avertissement au démarrage du daemon si `AI_DEV_FACTORY_RUNTIME_ROOT` n'est pas set (`_log("WARNING: AI_DEV_FACTORY_RUNTIME_ROOT not set — using dev fallback path")`), ou une assertion dans `bootstrap.sh` vérifiant que la DB canonique existe après migration.

---

## Observations non-bloquantes

**`runtime_resolver.py:64` — `_load_workers` lit depuis `runs_dir`, pas `state_dir`**

La fonction `resolve_ticket_run_dir()` charge le workers registry depuis `runs_dir` (inchangé). Désormais que `workers.json` vit dans `state_dir`, cette lookup peut rater si le registry a migré. Cohérence à vérifier.

**`board_service.py:_load_runtime_db` — double résolution RUNTIME_ROOT**

`get_board` résout déjà `rt = Path(runtime_root)` puis passe `project_root` à `_load_runtime_db`, qui relit RUNTIME_ROOT en interne. Doublon sans conséquence fonctionnelle, mais incohérent.

**`bootstrap.sh` — migration sans cleanup**

Le ticket énonce des "interdictions" dures (aucune DB dans worktree/clone). La migration copie vers la cible mais ne supprime pas les sources. En l'absence de cleanup, les anciennes DBs continuent d'exister — leur présence ne cause pas de régression immédiate grâce aux fix code, mais viole la lettre du ticket. Acceptable per la contrainte "migration progressive" mais à documenter comme dette.

---

## Bilan par livrable

| Livrable | Statut |
|---|---|
| Runtime ownership spec (docs) | ✅ |
| Migration bootstrap | ✅ |
| Suppression DB locales | ⚠️ Migration sans cleanup (acceptable) |
| Cleanup runtime artifacts | ⚠️ Non implémenté |
| Runtime hydration Docker | ✅ (bootstrap.sh copie la DB) |
| Board stable après restart | ✅ |
| Invariant checks runtime | ❌ Absent |
| Documentation architecture | ✅ |

---

## Corrections requises avant approbation

1. **Utiliser `resolve_state_dir()` / `resolve_logs_dir()`** dans `board_service.py` et `run_daemon.py`, ou supprimer ces fonctions du resolver — elles ne doivent pas rester du dead code.
2. **Corriger le fallback `runtime_db.py`** pour éviter la création de DB dans les worktrees en dev mode. Rétablir `git common-dir` comme fallback dev, ou imposer RUNTIME_ROOT avec une erreur explicite.
3. **Ajouter un invariant check minimal** au démarrage du daemon (warning ou error si RUNTIME_ROOT absent en contexte non-dev, ou log explicite du path résolu au démarrage).

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T116/reviews/implementation-review.md
- generated at: 2026-05-19T17:05:13Z

---

I have all the information I need. Let me write the review.

---

# Review — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Résumé exécutif

L'implémentation corrige les problèmes critiques en production (board DB path, workers registry, daemon logging) et maintient la compatibilité descendante. Elle est correcte pour le cas Docker/production. Trois défauts structurels nécessitent des corrections avant approbation.

---

## Scope compliance

L'implémentation est bornée au ticket. Pas de dérive de scope observée. Le plan approuvé est intégralement implémenté.

Les livrables couverts :
- ✅ Runtime ownership spec (décisions-log.md, runtime-layout.md)
- ✅ Migration bootstrap runtime (deploy/bootstrap.sh)
- ✅ Séparation state_dir / runs_dir
- ✅ Board stable après restart (board_service.py)
- ✅ File logging daemon vers RUNTIME_ROOT/logs/daemon.log
- ⚠️ Invariant checks runtime — **livrable explicite du ticket, absent**
- ⚠️ Suppression DB locales — migration uniquement, pas de cleanup (acceptable per contrainte "migration progressive")

---

## Problème #1 — BLOQUANT : `resolve_state_dir()` / `resolve_logs_dir()` sont du dead code

**Fichier :** `services/control_api/services/runtime_resolver.py:28-41`

Les deux fonctions ajoutées à l'étape 6 du plan ne sont jamais importées ni appelées. `board_service.py` et `run_daemon.py` dupliquent la logique de résolution en ligne chacun de leur côté :

```python
# board_service.py — inline, non extrait
runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
if runtime_root:
    db_path = Path(runtime_root) / ".runtime" / "ai-dev-factory.sqlite"

# run_daemon.py — inline, non extrait
if runtime_root:
    rt = Path(runtime_root)
    state_dir = rt / "state"
```

Résultat : l'abstraction "canonical resolver" existe mais n'est pas utilisée. Si le nom de l'env var change ou si la logique de résolution évolue, elle devra être corrigée à 3 endroits au lieu d'un.

**Correction attendue :** soit utiliser `resolve_state_dir()` dans `board_service.py` et `run_daemon.py`, soit supprimer ces helpers s'ils ne sont pas encore prêts à être intégrés.

---

## Problème #2 — BLOQUANT : `runtime_db.py` — le nouveau fallback crée des DB dans les worktrees

**Fichier :** `tools/agent_runner/runtime_db.py:80-83`

```python
# Dev fallback: this module lives at tools/agent_runner/runtime_db.py,
# so parent.parent.parent resolves to the repo root deterministically.
return Path(__file__).resolve().parent.parent.parent / _DB_FILENAME
```

Ce raisonnement est faux pour les processus workers. Quand `run_ticket.py` est exécuté depuis un worktree, Python charge `runtime_db.py` depuis la copie locale du worktree. `Path(__file__).resolve()` retourne alors `<worktree>/tools/agent_runner/runtime_db.py`, et `.parent.parent.parent` est la racine du worktree — pas le repo principal.

L'**ancien comportement** via `git rev-parse --git-common-dir` renvoyait toujours le common git dir (celui du clone principal), garantissant que tous les processus — y compris ceux lancés depuis des worktrees — partageaient **une seule DB**. Le nouveau fallback brise cette propriété en dev mode.

En Docker (RUNTIME_ROOT set), ce chemin n'est jamais atteint — le bug est donc invisible en production. Mais en dev local, il peut recréer exactement le problème décrit dans le ticket : DB fragmentées par worktree.

Le docstring du module (ligne 5-6) dit encore "resolved from the git common dir so all worktrees share one DB" — il est désormais incorrect.

**Correction attendue :** rétablir le fallback `git common-dir` (supprimer le subprocess uniquement si RUNTIME_ROOT est set, et conserver git common-dir en fallback dev), ou imposer explicitement RUNTIME_ROOT en dev (avec une erreur claire), ou conserver le fallback module-location **uniquement** en documentant qu'il est réservé à des invocations depuis le clone principal.

---

## Problème #3 — MOYEN : Invariant checks absents (livrable explicite du ticket)

Le ticket liste explicitement `invariant checks runtime` comme livrable. Aucun check n'est présent dans l'implémentation.

Un check minimal acceptable serait un avertissement au démarrage du daemon si `AI_DEV_FACTORY_RUNTIME_ROOT` n'est pas set (`_log("WARNING: AI_DEV_FACTORY_RUNTIME_ROOT not set — using dev fallback path")`), ou une assertion dans `bootstrap.sh` vérifiant que la DB canonique existe après migration.

---

## Observations non-bloquantes

**`runtime_resolver.py:64` — `_load_workers` lit depuis `runs_dir`, pas `state_dir`**

La fonction `resolve_ticket_run_dir()` charge le workers registry depuis `runs_dir` (inchangé). Désormais que `workers.json` vit dans `state_dir`, cette lookup peut rater si le registry a migré. Cohérence à vérifier.

**`board_service.py:_load_runtime_db` — double résolution RUNTIME_ROOT**

`get_board` résout déjà `rt = Path(runtime_root)` puis passe `project_root` à `_load_runtime_db`, qui relit RUNTIME_ROOT en interne. Doublon sans conséquence fonctionnelle, mais incohérent.

**`bootstrap.sh` — migration sans cleanup**

Le ticket énonce des "interdictions" dures (aucune DB dans worktree/clone). La migration copie vers la cible mais ne supprime pas les sources. En l'absence de cleanup, les anciennes DBs continuent d'exister — leur présence ne cause pas de régression immédiate grâce aux fix code, mais viole la lettre du ticket. Acceptable per la contrainte "migration progressive" mais à documenter comme dette.

---

## Bilan par livrable

| Livrable | Statut |
|---|---|
| Runtime ownership spec (docs) | ✅ |
| Migration bootstrap | ✅ |
| Suppression DB locales | ⚠️ Migration sans cleanup (acceptable) |
| Cleanup runtime artifacts | ⚠️ Non implémenté |
| Runtime hydration Docker | ✅ (bootstrap.sh copie la DB) |
| Board stable après restart | ✅ |
| Invariant checks runtime | ❌ Absent |
| Documentation architecture | ✅ |

---

## Corrections requises avant approbation

1. **Utiliser `resolve_state_dir()` / `resolve_logs_dir()`** dans `board_service.py` et `run_daemon.py`, ou supprimer ces fonctions du resolver — elles ne doivent pas rester du dead code.
2. **Corriger le fallback `runtime_db.py`** pour éviter la création de DB dans les worktrees en dev mode. Rétablir `git common-dir` comme fallback dev, ou imposer RUNTIME_ROOT avec une erreur explicite.
3. **Ajouter un invariant check minimal** au démarrage du daemon (warning ou error si RUNTIME_ROOT absent en contexte non-dev, ou log explicite du path résolu au démarrage).

IMPLEMENTATION_FIX_REQUIRED