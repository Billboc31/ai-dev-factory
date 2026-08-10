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


# T228 — Add autonomous “Unblock this ticket” recovery action to AI Workspace

**Source**: GitHub Issue #312

## Description

## Objective

Add an AI Workspace action that lets the user ask Claude to autonomously diagnose and recover a blocked AI Dev Factory ticket.

Example request:

> Unblock this ticket.

Claude should investigate why the active ticket is blocked, perform the authorized recovery work, restart the relevant pipeline step, and verify that the ticket is progressing again. If the blocker exposes an AI Dev Factory product bug, the action must create a documented GitHub issue.

## User story

As a remote AI Dev Factory user, I want to ask the integrated Workspace chat to unblock the current ticket so that Claude can inspect the pipeline, artifacts, logs, branches, and execution state without requiring me to diagnose each failure manually.

## Structured action

The Workspace should translate the request into a constrained Supervisor action similar to:

```json
{
  "action": "recover_ticket",
  "project_id": "ai-dev-factory",
  "ticket_id": "T226",
  "diagnose": true,
  "apply_safe_fixes": true,
  "retry_failed_stage": true,
  "create_bug_issue_when_detected": true
}
```

The active project and ticket must be resolved from the Workspace context when the user says “this ticket”.

## Recovery workflow

1. Collect the current ticket state.
2. Inspect the failed or blocked pipeline stage.
3. Read relevant logs and existing ticket artifacts.
4. Inspect repository and branch state when relevant.
5. Classify the blocker.
6. Produce a concise recovery plan.
7. Request confirmation before applying mutating recovery actions.
8. Apply only allowlisted and ticket-scoped fixes.
9. Retry the appropriate failed/blocked stage.
10. Verify that the ticket reaches the expected next state.
11. Return a recovery report to the chat.
12. When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue containing the evidence.

## Blocker classification

The recovery agent must distinguish at least:

- missing or malformed ticket artifact;
- stale readiness or rule evaluation;
- missing human approval;
- failed planner, implementation, review, fix-loop, or test execution;
- branch divergence or missing remote update;
- repository working-tree conflict;
- transient provider, network, or process failure;
- invalid project configuration;
- unsupported or inconsistent pipeline state;
- reproducible AI Dev Factory product bug;
- blocker requiring an explicit user decision.

## Allowed recovery actions

Subject to Supervisor authorization and confirmation, the action may:

- regenerate a missing derived artifact using the expected repository convention;
- correct a malformed ticket-scoped artifact;
- refresh readiness and rule evaluation;
- fetch or pull the configured ticket branch using the approved strategy;
- restart or retry the failed pipeline stage;
- restart an approved local AI Dev Factory service when required;
- run ticket-scoped diagnostics and tests;
- create a GitHub bug issue with diagnostic evidence;
- add the created issue URL to the ticket recovery report.

## Safety requirements

- Route all actions through the Supervisor.
- Do not give Claude unrestricted shell access.
- Do not accept arbitrary paths, commands, service names, or internal endpoints from the frontend or model.
- Restrict mutations to the active ticket, its configured branch, approved artifacts, and allowlisted services.
- Never fabricate or bypass human approval.
- When the blocker is “human approval missing”, explain what must be approved and stop at the approval gate.
- Never change readiness, rule, review, or test results merely to force the ticket forward.
- Do not modify `plan.md` directly when the expected workflow requires a plan-review or plan-fix artifact.
- Do not overwrite user changes or resolve merge conflicts automatically unless an explicit safe policy permits it.
- Show the proposed recovery actions before execution.
- Record diagnostics, confirmation, mutations, retries, and results in the audit trail.
- Prevent concurrent recovery sessions for the same ticket.
- Enforce a retry and iteration limit so the agent cannot enter an infinite fix loop.
- Stop and request user input when recovery would require a product decision or destructive operation.

## Automatic bug issue creation

When Claude identifies a reproducible bug in AI Dev Factory rather than a ticket-specific failure, it must create a deduplicated GitHub issue containing:

- concise title;
- affected pipeline stage;
- ticket and project identifiers;
- expected behavior;
- actual behavior;
- sanitized error message and relevant logs;
- reproduction steps;
- suspected component;
- recovery workaround, when available;
- links to related existing issues;
- originating recovery session identifier.

Before creating the issue, search open issues for an equivalent bug. If one exists, link it in the recovery report instead of creating a duplicate.

Secrets, credentials, private prompts, unrestricted logs, and sensitive local paths must not be included in the issue.

## UX requirements

- Add a suggested or explicit `Unblock ticket` action in the AI Workspace when the active ticket is blocked.
- Display live recovery stages:
  - `DIAGNOSING`
  - `PLAN_READY`
  - `AWAITING_CONFIRMATION`
  - `APPLYING_FIX`
  - `RETRYING_STAGE`
  - `VERIFYING`
  - `RECOVERED`
  - `NEEDS_USER_INPUT`
  - `BUG_REPORTED`
  - `FAILED`
- Show the detected root cause and the exact recovery operations before confirmation.
- Stream concise progress and relevant sanitized log excerpts.
- On success, show the new ticket state and next pipeline stage.
- On partial recovery, clearly state what remains blocked and what the user must do.
- When an issue is created or linked, show its URL in the conversation.

## Acceptance criteria

- “Unblock this ticket” resolves the active Workspace ticket without requiring its identifier to be repeated.
- Claude diagnoses the actual blocking stage using current pipeline state and artifacts.
- A clear root cause and recovery plan are shown before any mutation.
- The Supervisor executes only allowlisted, ticket-scoped recovery operations.
- Human approval gates are never bypassed or fabricated.
- A recoverable missing/malformed artifact can be repaired using the correct repository convention.
- A transient failed stage can be retried and its new result verified.
- The action verifies that the ticket moved to the expected next state before reporting success.
- Recovery stops after the configured retry/iteration limit.
- A reproducible platform bug results in a deduplicated, sanitized GitHub issue or a link to an existing equivalent issue.
- The final chat response includes diagnostics, actions performed, retry result, final ticket state, and any bug issue URL.
- Existing manual recovery controls continue to work.

## Out of scope

- Bypassing human review or approval.
- Silently changing business requirements or acceptance criteria.
- Unrestricted autonomous shell access.
- Destructive Git operations.
- Automatic resolution of ambiguous merge conflicts.
- Recovery across unrelated projects or tickets.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

The full suite's pre-existing failures are unrelated to this change — they affect `test_ticket_intelligence_api`, `test_ticket_readiness_api`, `test_ticket_timeline`, `test_traefik_separation`, `test_runtime_db`, and `test_supervisor_intelligence_analyze`, none of which touch the workspace or recovery code. The 136 failures and 14 errors were already present on the branch before this implementation.

The two test files we own are clean: **36/36 pass** (`test_workspace_recovery.py` + `test_supervisor_workspace.py`).

---

## Review

---

# PR Review — T228: Autonomous "Unblock this ticket" recovery action

## Résumé

L'implémentation couvre l'ensemble du périmètre fonctionnel du ticket : moteur de récupération (`recovery.py`), intégration Supervisor (`main.py`), interface frontend (`ProjectWorkspacePanel.jsx`), proxy API et 36 tests unitaires. L'architecture est saine — allowlist fermée, proposals immuables, fingerprinting SHA256, concurrence atomique. Deux défauts bloquants sont identifiés avant validation.

---

## Vérifications effectuées

- Lecture de l'ensemble des fichiers modifiés/créés identifiés par `git diff main`
- Contrôle de la couverture des 11 classes de bloqueur du ticket
- Contrôle de la couverture des 10 étapes UX du ticket
- Analyse du cycle de vie des sessions (`_active_sessions`, `_proposals`, `_results`)
- Analyse du modèle de sécurité : allowlist, validation des paramètres, fingerprint TOCTOU, gate d'approbation
- Analyse du workflow de création de bug issue (déduplication, sanitisation)
- Lecture de la suite de tests (`tests/test_workspace_recovery.py`, 36 cas)

---

## Points validés

**Sécurité — modèle de contrôle**
- Toutes les opérations passent par l'allowlist fermée `ALLOWLISTED_RECOVERY_OPS` ; les noms d'opérations et les paramètres sont des enums, pas des chaînes libres. Aucun accès shell générique (`shell=True` absent).
- Les proposals sont immuables après création : le frontend ne peut envoyer qu'un `proposal_id` à la confirmation, pas redéfinir les opérations.
- Fingerprint SHA256 calculé avant et après la fenêtre prepare→execute. Un changement d'état retourne 409 `PROPOSAL_STALE` — protection effective contre les races TOCTOU.
- La gate `MISSING_APPROVAL` ne déclenche aucune opération mutante (plan vide) et termine en `NEEDS_USER_INPUT`. Aucune fabrication d'approbation.
- Les opérations Git sont bornées à `git fetch origin <branch>` ; pas de reset, force-push, ni résolution automatique de conflits.
- `MAX_RECOVERY_ITERATIONS = 3` — boucle infinie impossible.
- Lock `_session_lock` avec try-finally — pas de session fantôme sur exception en prepare.
- Timeouts explicites sur tous les sous-processus (fetch 60 s, GitHub API 30 s).

**Classification bloqueur**
- Les 11 classes du ticket (`BlockerClass`) sont toutes implémentées dans `classify_blocker()` via heuristiques déterministes, sans LLM ni input frontend.

**Étapes UX**
- Les 10 stages du ticket (`RecoveryStage`) sont présents et mappés à des couleurs distinctes dans `RecoveryStageIndicator`.

**Bug issue — déduplication et sanitisation**
- Signature déterministe (SHA256 de champs structurés uniquement, pas de texte libre LLM).
- Recherche d'issue existante avant création — pas de spam.
- Corps de l'issue construit à partir de champs structurés uniquement ; pas de logs bruts, pas de paths locaux, pas de secrets.
- URL de l'issue ajoutée au recovery report.

**Tests**
- 36 cas couvrant : absence de mutations en phase prepare, rejet d'opérations arbitraires, rejet de params arbitraires, rejet de sessions concurrentes, enforcement de la limite d'itérations, déduplication bug, résolution du ticket actif, vérification de progression, endpoint de polling.

---

## Problèmes détectés

### [BLOQUANT 1] Deadlock de session sur `MISSING_APPROVAL`

**Localisation** : `services/supervisor/main.py`, ligne ~3102 (`_prepare_recovery`) et ligne ~3332 (`_execute_recovery` finally).

**Comportement** : Quand `classify_blocker()` retourne `MISSING_APPROVAL`, `build_recovery_plan()` produit une liste vide. Dans le frontend, le bouton "Confirm Recovery" est désactivé (`disabled={!action.operations?.length}`), donc `_execute_recovery()` n'est jamais appelé. Or c'est l'unique chemin qui retire la session de `_active_sessions`. La session reste en `PLAN_READY` indéfiniment.

**Impact** : Toute tentative ultérieure d'"Unblock this ticket" sur le même ticket retourne immédiatement `RECOVERY_IN_PROGRESS`. L'utilisateur est bloqué jusqu'au redémarrage du Supervisor.

**Correction attendue** (l'une ou l'autre) :
- Option A — Dans `_prepare_recovery()`, après `build_recovery_plan()`, si le plan est vide : nettoyer `_active_sessions[ticket_id]` et retourner directement la réponse `NEEDS_USER_INPUT` sans stocker de session active.
- Option B — Activer le bouton Confirm pour les plans vides et laisser `_execute_recovery()` atteindre son bloc `NEEDS_USER_INPUT` (ligne ~3295), qui nettoie déjà la session.

Un test couvrant ce chemin exact est requis.

---

### [BLOQUANT 2] Bug issue non créée quand la récupération échoue sur `PRODUCT_BUG`

**Localisation** : `services/supervisor/main.py`, ligne ~3251 — condition `if advanced:` encapsulant la logique de création d'issue (lignes ~3254–3287).

**Comportement** : Si les opérations de recovery échouent et que `verify_ticket_progress()` retourne `False`, `advanced` est `False`, le bloc de création d'issue n'est pas exécuté, et la session termine en `FAILED` ou `NEEDS_USER_INPUT` sans aucune issue GitHub créée.

**Impact** : Violation directe du ticket — *"When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue"* — l'évidence est perdue précisément dans le cas où le bug est le plus difficile à reproduire manuellement.

**Correction attendue** : Déplacer la logique de création/liaison d'issue hors du bloc `if advanced:`, conditionner uniquement sur `proposal.blocker_class == BlockerClass.PRODUCT_BUG`. La progression du ticket et la création de l'issue sont des sorties orthogonales.

Un test vérifiant la création d'issue quand `advanced=False` et `blocker_class=PRODUCT_BUG` est requis.

---

## Risques éventuels

**MEDIUM — Pas de test de régression sur les capacités Workspace existantes**
La réponse du Supervisor charge les capabilities via `_WORKSPACE_CAPABILITIES`. L'ajout de `recover_ticket` n'est pas testé en interaction avec les autres capabilities (`restart_daemon`, `resume_execution`, etc.). Un test vérifiant l'absence de régression sur le routage des actions existantes est recommandé.

**MEDIUM — Pas de test E2E du chemin MISSING_APPROVAL dans l'UI**
Même après correction du deadlock, le parcours utilisateur complet (message → DIAGNOSING → PLAN_READY → message explicatif sans bouton Confirm → retour possible à "Unblock") n'est couvert par aucun test d'intégration.

**LOW — Incohérence UX sur le bouton Confirm désactivé**
Après correction de l'option A, l'utilisateur verra une confirmation card avec un bouton désactivé et aucun message explicatif visible sur la raison (`MISSING_APPROVAL`). Il faudrait afficher le message d'explication directement dans la card plutôt que de laisser le bouton grisé sans contexte.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **[obligatoire]** Corriger le deadlock session `MISSING_APPROVAL` dans `_prepare_recovery()` (option A ou B décrite ci-dessus) et ajouter un test vérifiant que `_active_sessions` ne retient pas de session après un plan vide.

2. **[obligatoire]** Déplacer la création de bug issue hors du bloc `if advanced:`, la conditionner sur `blocker_class == PRODUCT_BUG` uniquement, et ajouter un test vérifiant la création quand `advanced=False`.

3. **[recommandé]** Ajouter un test de non-régression sur les capabilities Workspace existantes après enregistrement de `recover_ticket`.

4. **[recommandé]** Afficher le message MISSING_APPROVAL directement dans la `RecoveryConfirmCard` (classe de bloqueur + explication de ce que l'utilisateur doit faire), pas uniquement via le bouton grisé.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T228/reviews/implementation-review.md
- generated at: 2026-08-05T22:00:11Z

---

---

# PR Review — T228: Autonomous "Unblock this ticket" recovery action

## Résumé

L'implémentation couvre l'ensemble du périmètre fonctionnel du ticket : moteur de récupération (`recovery.py`), intégration Supervisor (`main.py`), interface frontend (`ProjectWorkspacePanel.jsx`), proxy API et 36 tests unitaires. L'architecture est saine — allowlist fermée, proposals immuables, fingerprinting SHA256, concurrence atomique. Deux défauts bloquants sont identifiés avant validation.

---

## Vérifications effectuées

- Lecture de l'ensemble des fichiers modifiés/créés identifiés par `git diff main`
- Contrôle de la couverture des 11 classes de bloqueur du ticket
- Contrôle de la couverture des 10 étapes UX du ticket
- Analyse du cycle de vie des sessions (`_active_sessions`, `_proposals`, `_results`)
- Analyse du modèle de sécurité : allowlist, validation des paramètres, fingerprint TOCTOU, gate d'approbation
- Analyse du workflow de création de bug issue (déduplication, sanitisation)
- Lecture de la suite de tests (`tests/test_workspace_recovery.py`, 36 cas)

---

## Points validés

**Sécurité — modèle de contrôle**
- Toutes les opérations passent par l'allowlist fermée `ALLOWLISTED_RECOVERY_OPS` ; les noms d'opérations et les paramètres sont des enums, pas des chaînes libres. Aucun accès shell générique (`shell=True` absent).
- Les proposals sont immuables après création : le frontend ne peut envoyer qu'un `proposal_id` à la confirmation, pas redéfinir les opérations.
- Fingerprint SHA256 calculé avant et après la fenêtre prepare→execute. Un changement d'état retourne 409 `PROPOSAL_STALE` — protection effective contre les races TOCTOU.
- La gate `MISSING_APPROVAL` ne déclenche aucune opération mutante (plan vide) et termine en `NEEDS_USER_INPUT`. Aucune fabrication d'approbation.
- Les opérations Git sont bornées à `git fetch origin <branch>` ; pas de reset, force-push, ni résolution automatique de conflits.
- `MAX_RECOVERY_ITERATIONS = 3` — boucle infinie impossible.
- Lock `_session_lock` avec try-finally — pas de session fantôme sur exception en prepare.
- Timeouts explicites sur tous les sous-processus (fetch 60 s, GitHub API 30 s).

**Classification bloqueur**
- Les 11 classes du ticket (`BlockerClass`) sont toutes implémentées dans `classify_blocker()` via heuristiques déterministes, sans LLM ni input frontend.

**Étapes UX**
- Les 10 stages du ticket (`RecoveryStage`) sont présents et mappés à des couleurs distinctes dans `RecoveryStageIndicator`.

**Bug issue — déduplication et sanitisation**
- Signature déterministe (SHA256 de champs structurés uniquement, pas de texte libre LLM).
- Recherche d'issue existante avant création — pas de spam.
- Corps de l'issue construit à partir de champs structurés uniquement ; pas de logs bruts, pas de paths locaux, pas de secrets.
- URL de l'issue ajoutée au recovery report.

**Tests**
- 36 cas couvrant : absence de mutations en phase prepare, rejet d'opérations arbitraires, rejet de params arbitraires, rejet de sessions concurrentes, enforcement de la limite d'itérations, déduplication bug, résolution du ticket actif, vérification de progression, endpoint de polling.

---

## Problèmes détectés

### [BLOQUANT 1] Deadlock de session sur `MISSING_APPROVAL`

**Localisation** : `services/supervisor/main.py`, ligne ~3102 (`_prepare_recovery`) et ligne ~3332 (`_execute_recovery` finally).

**Comportement** : Quand `classify_blocker()` retourne `MISSING_APPROVAL`, `build_recovery_plan()` produit une liste vide. Dans le frontend, le bouton "Confirm Recovery" est désactivé (`disabled={!action.operations?.length}`), donc `_execute_recovery()` n'est jamais appelé. Or c'est l'unique chemin qui retire la session de `_active_sessions`. La session reste en `PLAN_READY` indéfiniment.

**Impact** : Toute tentative ultérieure d'"Unblock this ticket" sur le même ticket retourne immédiatement `RECOVERY_IN_PROGRESS`. L'utilisateur est bloqué jusqu'au redémarrage du Supervisor.

**Correction attendue** (l'une ou l'autre) :
- Option A — Dans `_prepare_recovery()`, après `build_recovery_plan()`, si le plan est vide : nettoyer `_active_sessions[ticket_id]` et retourner directement la réponse `NEEDS_USER_INPUT` sans stocker de session active.
- Option B — Activer le bouton Confirm pour les plans vides et laisser `_execute_recovery()` atteindre son bloc `NEEDS_USER_INPUT` (ligne ~3295), qui nettoie déjà la session.

Un test couvrant ce chemin exact est requis.

---

### [BLOQUANT 2] Bug issue non créée quand la récupération échoue sur `PRODUCT_BUG`

**Localisation** : `services/supervisor/main.py`, ligne ~3251 — condition `if advanced:` encapsulant la logique de création d'issue (lignes ~3254–3287).

**Comportement** : Si les opérations de recovery échouent et que `verify_ticket_progress()` retourne `False`, `advanced` est `False`, le bloc de création d'issue n'est pas exécuté, et la session termine en `FAILED` ou `NEEDS_USER_INPUT` sans aucune issue GitHub créée.

**Impact** : Violation directe du ticket — *"When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue"* — l'évidence est perdue précisément dans le cas où le bug est le plus difficile à reproduire manuellement.

**Correction attendue** : Déplacer la logique de création/liaison d'issue hors du bloc `if advanced:`, conditionner uniquement sur `proposal.blocker_class == BlockerClass.PRODUCT_BUG`. La progression du ticket et la création de l'issue sont des sorties orthogonales.

Un test vérifiant la création d'issue quand `advanced=False` et `blocker_class=PRODUCT_BUG` est requis.

---

## Risques éventuels

**MEDIUM — Pas de test de régression sur les capacités Workspace existantes**
La réponse du Supervisor charge les capabilities via `_WORKSPACE_CAPABILITIES`. L'ajout de `recover_ticket` n'est pas testé en interaction avec les autres capabilities (`restart_daemon`, `resume_execution`, etc.). Un test vérifiant l'absence de régression sur le routage des actions existantes est recommandé.

**MEDIUM — Pas de test E2E du chemin MISSING_APPROVAL dans l'UI**
Même après correction du deadlock, le parcours utilisateur complet (message → DIAGNOSING → PLAN_READY → message explicatif sans bouton Confirm → retour possible à "Unblock") n'est couvert par aucun test d'intégration.

**LOW — Incohérence UX sur le bouton Confirm désactivé**
Après correction de l'option A, l'utilisateur verra une confirmation card avec un bouton désactivé et aucun message explicatif visible sur la raison (`MISSING_APPROVAL`). Il faudrait afficher le message d'explication directement dans la card plutôt que de laisser le bouton grisé sans contexte.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **[obligatoire]** Corriger le deadlock session `MISSING_APPROVAL` dans `_prepare_recovery()` (option A ou B décrite ci-dessus) et ajouter un test vérifiant que `_active_sessions` ne retient pas de session après un plan vide.

2. **[obligatoire]** Déplacer la création de bug issue hors du bloc `if advanced:`, la conditionner sur `blocker_class == PRODUCT_BUG` uniquement, et ajouter un test vérifiant la création quand `advanced=False`.

3. **[recommandé]** Ajouter un test de non-régression sur les capabilities Workspace existantes après enregistrement de `recover_ticket`.

4. **[recommandé]** Afficher le message MISSING_APPROVAL directement dans la `RecoveryConfirmCard` (classe de bloqueur + explication de ce que l'utilisateur doit faire), pas uniquement via le bouton grisé.

IMPLEMENTATION_FIX_REQUIRED