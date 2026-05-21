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


# T122 — T122 — Dashboard action audit trail

**Source**: GitHub Issue #82

## Description

Add an audit trail for dashboard ticket actions (approve plan, retry, archive, abort, run next). Store audit events, expose them through the control API, and display them in the ticket detail page with timestamp, status, and error messages.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Everything looks correct. Here's a summary of all changes made:

---

## Changes made

**Backend — 3 files modified**

- `services/control_api/models/schemas.py` — Added `AuditEvent` Pydantic model (`id`, `event_type`, `message`, `metadata`, `created_at`).

- `services/control_api/main.py` — Added `tools/agent_runner` to sys.path and imported `runtime_db`, then stored `app.state.db_path = _runtime_db.get_db_path()` in `create_app()`.

- `services/control_api/routes/tickets.py` — Added `runtime_db` import (same sys.path pattern), `_db_path()` / `_log_action()` helpers, audit logging on all 9 action endpoints, and `GET /tickets/{ticket_id}/audit-log` endpoint filtering events by `event_type` prefix `"action:"`.

**Frontend — 3 files modified/created**

- `apps/dashboard/src/api/tickets.js` — Added `getAuditLog(id)` calling `GET /tickets/{id}/audit-log`.

- `apps/dashboard/src/components/AuditLog.jsx` *(new)* — Self-fetching table component with timestamp, action (stripped of `action:` prefix), ok/error badge, and message columns. Renders an empty state when no events exist.

- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Added `'audit'` to `TABS`, imported `AuditLog`, and renders `<AuditLog ticketId={id} />` when that tab is active (outside the tabLoading/TAB_FETCHERS flow, so it manages its own fetch lifecycle).

---

## Review

I have enough information to write a complete review.

---

# PR Review — T122: Dashboard action audit trail

## Résumé

L'implémentation couvre l'ensemble du scope défini dans le plan : logging audit sur les 9 endpoints d'action, endpoint `GET /tickets/{id}/audit-log`, schéma `AuditEvent`, API frontend `getAuditLog`, composant `AuditLog.jsx`, et onglet "Audit" dans `TicketDetailPage`. La structure est propre et cohérente avec les conventions du codebase.

Un problème de robustesse bloquant a été identifié : les exceptions levées par le logging audit peuvent masquer un résultat d'action réussi et faire retourner HTTP 500 au client.

## Vérifications effectuées

- Conformité du plan d'implémentation (9 endpoints, endpoint audit-log, schéma Pydantic, composant frontend, onglet)
- Signature `append_runtime_event` vs appels dans `_log_action`
- Comportement du composant `AuditLog` vis-à-vis des critères d'acceptation
- Filtrage `event_type.startswith("action:")` et ordre de tri (id DESC = created_at DESC)
- Gestion du cas "pas d'événements" (HTTP 200 + liste vide)
- Gestion `db_path = None` dans `_db_path()` et `get_audit_log`
- Comportement du remontage React lors du changement d'onglet

## Points validés

- **Couverture complète** : les 9 endpoints (`approve-plan`, `request-plan-fix`, `approve-implementation`, `request-implementation-fix`, `run-next`, `commit`, `push`, `checkpoint`, `archive`) appellent tous `_log_action` après la construction du résultat.
- **Signature correcte** : `_log_action` appelle `runtime_db.append_runtime_event(db, ticket_id, event_type=..., message=..., metadata=...)` — correspond exactement au paramètre `metadata: dict | None` (pas `metadata_json`).
- **Filtrage DB correct** : `get_audit_log` filtre les lignes sur `event_type.startswith("action:")` en application code, ce qui est approprié étant donné que `list_runtime_events` ne supporte pas de filtre de préfixe.
- **Schéma Pydantic** : `AuditEvent(id, event_type, message, metadata, created_at)` correct, `metadata` est `dict | None`.
- **Désérialisation DB** : `json.loads(e["metadata_json"]) if e.get("metadata_json") else None` — conforme au stockage effectué par `runtime_db`.
- **Onglet "Audit" React** : rendu conditionnel `tab === 'audit'` entraîne un unmount/remount à chaque switch d'onglet, ce qui déclenche un nouveau fetch dans `useEffect([ticketId])`. Critère d'acceptation "refreshing the Audit tab" satisfait.
- **Empty state** : `events.length === 0` → texte "No audit events yet." — correct.
- **Badge de statut** : `e.metadata?.ok ?? true` — valeur par défaut sûre si metadata absent.
- **`app.state.db_path`** injecté dans `create_app()` via `_runtime_db.get_db_path()` — disponible dans tous les handlers via `_db_path(request)`.
- **Ordre des événements** : `list_runtime_events` trie `ORDER BY id DESC` (AUTOINCREMENT ≡ ordre chronologique) — conforme au plan "ordered by created_at descending".

## Problèmes détectés

### BLOQUANT — `_log_action` sans gestion d'erreur (tickets.py:34-45)

```python
def _log_action(request, ticket_id, action, result):
    db = _db_path(request)
    if db is None:
        return
    msg = ...
    runtime_db.append_runtime_event(db, ...)  # ← aucun try/except
```

**Problème** : Si `append_runtime_event` lève une exception (verrou SQLite, disque plein, corruption), l'exception se propage dans le handler FastAPI et retourne HTTP 500 au client — alors que l'action sous-jacente (`subprocess_runner.approve_plan(...)` etc.) a déjà réussi.

Le client interprète ce 500 comme un échec de l'action et peut décider de réessayer, créant des effets de bord (double commit, double push, etc.). La règle "never mask a completed action" s'applique ici.

**Correction attendue** — envelopper l'appel DB dans un try/except dans `_log_action` :
```python
def _log_action(request, ticket_id, action, result):
    db = _db_path(request)
    if db is None:
        return
    msg = f"{action} ok" if result.ok else f"{action} failed: {result.stderr or result.message}"
    try:
        runtime_db.append_runtime_event(
            db, ticket_id,
            event_type=f"action:{action}",
            message=msg,
            metadata={"ok": result.ok, "returncode": result.returncode},
        )
    except Exception:
        logger.exception("audit log write failed for %s/%s (non-fatal)", ticket_id, action)
```

### Mineur — `run-next` audit reflect dispatch, pas le résultat réel (tickets.py:168-184)

Le background thread lance `subprocess_runner.run_next(...)` de manière asynchrone, mais l'événement est enregistré immédiatement avec `ok=True`. Si le subprocess échoue, l'audit log montre toujours "run-next ok". C'est une conséquence de la conception async du plan (logging après retour du `ActionResult`), mais le message `"run-next dispatched in background"` est suffisamment explicite pour ne pas induire en erreur.

### Mineur — Troncature silencieuse à 100 événements (runtime_db.py:271, tickets.py:233)

`list_runtime_events` a un `limit=100` par défaut. L'endpoint `get_audit_log` ne surcharge pas cette valeur. Pour des tickets à forte activité (tests en boucle), les événements anciens sont silencieusement exclus sans indication dans la réponse. Pas bloquant pour un v1 mais à noter.

### Mineur — Injection `sys.path` dupliquée

`main.py` et `routes/tickets.py` injectent tous les deux `tools/agent_runner` dans `sys.path` indépendamment. Fonctionnel mais redondant — cohérent avec le pattern existant du codebase.

## Risques éventuels

- En production sous Docker (`AI_DEV_FACTORY_RUNTIME_ROOT` défini), la résolution DB est stable. En dev sans l'env var, `get_db_path()` exécute `git rev-parse` au démarrage — cela peut lentement échouer dans des contextes CI non-git (retombe sur le path module-relatif, pas de `None`).
- Le `sys.path.insert(0, ...)` au niveau module dans `routes/tickets.py` est un side-effect global déclenché à l'import — risque théorique en tests parallèles, mais conforme au pattern de `main.py`.

## Décision

- IMPLEMENTATION_FIX_REQUIRED

## Actions demandées

1. **[Bloquant]** Envelopper l'appel `runtime_db.append_runtime_event(...)` dans `_log_action` avec un `try/except Exception` loggant l'erreur sans la propager — afin qu'une failure du logging audit ne retourne jamais HTTP 500 pour une action qui a réussi.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T122/reviews/implementation-review.md
- generated at: 2026-05-21T12:26:00Z

---

I have enough information to write a complete review.

---

# PR Review — T122: Dashboard action audit trail

## Résumé

L'implémentation couvre l'ensemble du scope défini dans le plan : logging audit sur les 9 endpoints d'action, endpoint `GET /tickets/{id}/audit-log`, schéma `AuditEvent`, API frontend `getAuditLog`, composant `AuditLog.jsx`, et onglet "Audit" dans `TicketDetailPage`. La structure est propre et cohérente avec les conventions du codebase.

Un problème de robustesse bloquant a été identifié : les exceptions levées par le logging audit peuvent masquer un résultat d'action réussi et faire retourner HTTP 500 au client.

## Vérifications effectuées

- Conformité du plan d'implémentation (9 endpoints, endpoint audit-log, schéma Pydantic, composant frontend, onglet)
- Signature `append_runtime_event` vs appels dans `_log_action`
- Comportement du composant `AuditLog` vis-à-vis des critères d'acceptation
- Filtrage `event_type.startswith("action:")` et ordre de tri (id DESC = created_at DESC)
- Gestion du cas "pas d'événements" (HTTP 200 + liste vide)
- Gestion `db_path = None` dans `_db_path()` et `get_audit_log`
- Comportement du remontage React lors du changement d'onglet

## Points validés

- **Couverture complète** : les 9 endpoints (`approve-plan`, `request-plan-fix`, `approve-implementation`, `request-implementation-fix`, `run-next`, `commit`, `push`, `checkpoint`, `archive`) appellent tous `_log_action` après la construction du résultat.
- **Signature correcte** : `_log_action` appelle `runtime_db.append_runtime_event(db, ticket_id, event_type=..., message=..., metadata=...)` — correspond exactement au paramètre `metadata: dict | None` (pas `metadata_json`).
- **Filtrage DB correct** : `get_audit_log` filtre les lignes sur `event_type.startswith("action:")` en application code, ce qui est approprié étant donné que `list_runtime_events` ne supporte pas de filtre de préfixe.
- **Schéma Pydantic** : `AuditEvent(id, event_type, message, metadata, created_at)` correct, `metadata` est `dict | None`.
- **Désérialisation DB** : `json.loads(e["metadata_json"]) if e.get("metadata_json") else None` — conforme au stockage effectué par `runtime_db`.
- **Onglet "Audit" React** : rendu conditionnel `tab === 'audit'` entraîne un unmount/remount à chaque switch d'onglet, ce qui déclenche un nouveau fetch dans `useEffect([ticketId])`. Critère d'acceptation "refreshing the Audit tab" satisfait.
- **Empty state** : `events.length === 0` → texte "No audit events yet." — correct.
- **Badge de statut** : `e.metadata?.ok ?? true` — valeur par défaut sûre si metadata absent.
- **`app.state.db_path`** injecté dans `create_app()` via `_runtime_db.get_db_path()` — disponible dans tous les handlers via `_db_path(request)`.
- **Ordre des événements** : `list_runtime_events` trie `ORDER BY id DESC` (AUTOINCREMENT ≡ ordre chronologique) — conforme au plan "ordered by created_at descending".

## Problèmes détectés

### BLOQUANT — `_log_action` sans gestion d'erreur (tickets.py:34-45)

```python
def _log_action(request, ticket_id, action, result):
    db = _db_path(request)
    if db is None:
        return
    msg = ...
    runtime_db.append_runtime_event(db, ...)  # ← aucun try/except
```

**Problème** : Si `append_runtime_event` lève une exception (verrou SQLite, disque plein, corruption), l'exception se propage dans le handler FastAPI et retourne HTTP 500 au client — alors que l'action sous-jacente (`subprocess_runner.approve_plan(...)` etc.) a déjà réussi.

Le client interprète ce 500 comme un échec de l'action et peut décider de réessayer, créant des effets de bord (double commit, double push, etc.). La règle "never mask a completed action" s'applique ici.

**Correction attendue** — envelopper l'appel DB dans un try/except dans `_log_action` :
```python
def _log_action(request, ticket_id, action, result):
    db = _db_path(request)
    if db is None:
        return
    msg = f"{action} ok" if result.ok else f"{action} failed: {result.stderr or result.message}"
    try:
        runtime_db.append_runtime_event(
            db, ticket_id,
            event_type=f"action:{action}",
            message=msg,
            metadata={"ok": result.ok, "returncode": result.returncode},
        )
    except Exception:
        logger.exception("audit log write failed for %s/%s (non-fatal)", ticket_id, action)
```

### Mineur — `run-next` audit reflect dispatch, pas le résultat réel (tickets.py:168-184)

Le background thread lance `subprocess_runner.run_next(...)` de manière asynchrone, mais l'événement est enregistré immédiatement avec `ok=True`. Si le subprocess échoue, l'audit log montre toujours "run-next ok". C'est une conséquence de la conception async du plan (logging après retour du `ActionResult`), mais le message `"run-next dispatched in background"` est suffisamment explicite pour ne pas induire en erreur.

### Mineur — Troncature silencieuse à 100 événements (runtime_db.py:271, tickets.py:233)

`list_runtime_events` a un `limit=100` par défaut. L'endpoint `get_audit_log` ne surcharge pas cette valeur. Pour des tickets à forte activité (tests en boucle), les événements anciens sont silencieusement exclus sans indication dans la réponse. Pas bloquant pour un v1 mais à noter.

### Mineur — Injection `sys.path` dupliquée

`main.py` et `routes/tickets.py` injectent tous les deux `tools/agent_runner` dans `sys.path` indépendamment. Fonctionnel mais redondant — cohérent avec le pattern existant du codebase.

## Risques éventuels

- En production sous Docker (`AI_DEV_FACTORY_RUNTIME_ROOT` défini), la résolution DB est stable. En dev sans l'env var, `get_db_path()` exécute `git rev-parse` au démarrage — cela peut lentement échouer dans des contextes CI non-git (retombe sur le path module-relatif, pas de `None`).
- Le `sys.path.insert(0, ...)` au niveau module dans `routes/tickets.py` est un side-effect global déclenché à l'import — risque théorique en tests parallèles, mais conforme au pattern de `main.py`.

## Décision

- IMPLEMENTATION_FIX_REQUIRED

## Actions demandées

1. **[Bloquant]** Envelopper l'appel `runtime_db.append_runtime_event(...)` dans `_log_action` avec un `try/except Exception` loggant l'erreur sans la propager — afin qu'une failure du logging audit ne retourne jamais HTTP 500 pour une action qui a réussi.

IMPLEMENTATION_FIX_REQUIRED