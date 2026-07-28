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


# T225 — Add persistent AI Project Workspace with controlled capabilities

**Source**: GitHub Issue #308

## Description

# Context

AI Dev Factory should provide a persistent AI workspace available from every project page, similar to Cursor's chat experience. However, it must not become a replacement for the AI Dev Factory workflow.

The AI should help users operate and understand the project, while preserving the principle that all functional development goes through GitHub issues and the existing pipeline.

**Every request issued from this workspace must be handled by the Supervisor.** The AI workspace is only a conversational interface; it never performs actions directly.

# Goal

Introduce a persistent AI workspace attached to each project that can answer questions, diagnose problems and execute controlled project actions through the Supervisor.

# Architecture

- The AI Workspace sends every user request to the Supervisor.
- The Supervisor decides whether the request is informational or actionable.
- Only the Supervisor is allowed to invoke platform capabilities.
- The AI Workspace never bypasses the Supervisor or directly calls internal services.

# Allowed capabilities

The AI may:

- Explain project status.
- Explain ticket states and workflow decisions.
- Diagnose blocked tickets.
- Analyze logs and test failures.
- Search project documentation.
- Read repository files.
- Explain configuration files.
- Create GitHub issues from user requests.
- Request project actions (resume execution, rerun intelligence, rerun dependency analysis, deployments, etc.), which are executed by the Supervisor after validation.

# Forbidden capabilities

The AI must NOT:

- Implement new features directly.
- Generate production code instead of creating an issue.
- Modify business source code.
- Bypass the GitHub Issue -> AI Dev Factory workflow.
- Bypass the Supervisor.
- Automatically create commits or pull requests for functional changes.

If the user requests a new feature or bug fix, the AI should propose creating a GitHub issue instead of editing the code.

# Acceptance Criteria

- Every project has its own persistent AI workspace.
- The workspace remains available while navigating through the project.
- The AI automatically receives the current project context.
- Every action requested from the workspace is routed through the Supervisor.
- Functional development requests are redirected to GitHub issue creation.
- Only explicitly allowed actions can be executed by the Supervisor on behalf of the AI.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 7 files are accounted for. Here's a summary of what was implemented:

---

## Changes Summary

### Files created (3 new)

**`services/control_api/routes/workspace.py`**
Thin proxy: validates project exists via `resolve_project` dependency, then forwards the request body to the Supervisor's workspace endpoints. Never calls AI, GitHub, or internal services directly.

**`apps/dashboard/src/api/workspace.js`**
Three axios API calls: `postWorkspaceMessage`, `confirmWorkspaceAction`, `confirmWorkspaceIssue` — all routing through `/api/projects/{id}/workspace/*`.

**`apps/dashboard/src/components/ProjectWorkspacePanel.jsx`**
Collapsible right-side panel (w-80, part of the flex layout — survives navigation). Maintains per-project conversation history in component state, resets on project switch. Shows confirmation cards for `actionable` (yellow) and `functional_dev` (blue) responses. Sends only opaque `action_id`/`draft_id` tokens on confirmation — never constructs internal arguments.

### Files modified (4)

**`services/supervisor/main.py`** (+451 lines)
Three new endpoints:
- `POST /workspace/projects/{id}/chat` — loads project context, calls Anthropic API via httpx, classifies intent, stores pending action/draft with UUID, returns structured response.
- `POST /workspace/projects/{id}/actions/confirm` — validates action_id + project match + capability allowlist, then executes via existing Supervisor functions.
- `POST /workspace/projects/{id}/issues/confirm` — validates draft_id + project match, calls `gh issue create`, returns issue URL.

**`services/control_api/main.py`** — imports `workspace` module, registers `workspace.project_router`.

**`apps/dashboard/src/App.jsx`** — adds `workspaceOpen` state, passes toggle to sidebar, renders `<ProjectWorkspacePanel>` as a flex sibling (outside `<Routes>` so it persists across navigation).

**`apps/dashboard/src/components/ProjectSidebar.jsx`** — adds "AI Workspace" toggle button in the project nav section, highlighted when open.

### Known limits

- `rerun_intelligence` and `trigger_deployment` capabilities are registered in the allowlist and proposed by the AI, but their confirmation execution returns a helpful message directing to the platform UI — they require additional context (ticket ID, environment config) not available from the workspace alone.
- Pending actions/issues are stored in-memory only; they are lost on Supervisor restart.
- AI provider is always Anthropic via `ANTHROPIC_API_KEY`; the model defaults to `claude-sonnet-4-6` and is overridable via `WORKSPACE_AI_MODEL` env var.

---

## Review

Now I have everything I need. Writing the review.

---

# PR Review — T225 : Add persistent AI Project Workspace with controlled capabilities

## Résumé

L'implémentation introduit un panneau de workspace IA persistant sur toutes les pages projet, accessible via un bouton bascule dans la sidebar. L'architecture en trois couches (Frontend → Control API → Supervisor) est correctement respectée : la Control API est un proxy authentifié pur, et le Supervisor détient toute la logique (appel IA, enforcement des capacités, création d'issues GitHub). Les critères d'acceptance du ticket sont majoritairement satisfaits.

## Vérifications effectuées

- Diff complet lu (16 fichiers, ~1854 lignes ajoutées)
- Chemin de routing tracé bout-en-bout : Frontend → Control API → Supervisor
- Enforcement de l'allowlist de capacités vérifié ligne par ligne
- Système de tokens UUID opaques vérifié
- Mécanisme de persistance du panneau vérifié (hors `<Routes>`)
- Validation croisée action/projet sur les endpoints de confirmation
- Prompt système inspecté pour conformité aux contraintes
- Gestion des erreurs relue
- Limites connues croisées avec `implementation-output.md` et `plan.md`

## Points validés

1. **Tout passe par le Supervisor** — `control_api/routes/workspace.py` n'appelle ni provider IA, ni GitHub, ni service interne. Il forward uniquement vers le Supervisor via `_forward()`.

2. **Allowlist deny-by-default** — `_WORKSPACE_CAPABILITIES` définit exactement 5 capacités (supervisor.main.py:2876–2897). Toute capacité proposée par l'IA non présente dans ce dict est rejetée à la ligne 3182 : le `proposed_action` est annulé, le `intent` recalé à `informational`.

3. **Tokens UUID opaques** — Les `action_id` et `draft_id` sont générés côté Supervisor (`str(uuid.uuid4())`). Le frontend ne construit jamais d'arguments internes : il ne renvoie que le token opaque à la confirmation.

4. **Confirmation obligatoire avant toute mutation** — Actions et drafts d'issues sont stockés en attente jusqu'à confirmation explicite via `/actions/confirm` ou `/issues/confirm`.

5. **Functional dev → issue GitHub uniquement** — L'intent `functional_dev` retourne un draft d'issue, jamais de code, commit ou PR.

6. **Isolation par projet à la confirmation** — Les deux endpoints de confirmation vérifient `action["project_id"] != project_id` et retournent 403 en cas de mismatch (supervisor.main.py:3227–3228, 3258–3259).

7. **Persistance du panneau** — `<ProjectWorkspacePanel>` est rendu en dehors de `<Routes>` comme frère flex dans App.jsx. La conversation se réinitialise uniquement au changement de `projectId` via `useEffect([projectId])`.

8. **Logs traçables** — Toutes les opérations workspace loguent `project_id`, `intent`, `capability`, `action_id`, `draft_id`.

9. **Prompt système conforme** — Les interdictions du ticket (pas de code, pas de commit, pas de contournement du workflow GitHub, pas de secrets) sont explicitement inscrites dans `_WORKSPACE_SYSTEM_PROMPT`.

## Problèmes détectés

### P1 — Capacités stub présentées comme disponibles mais en échec à la confirmation [BLOQUANT]

`rerun_intelligence` et `trigger_deployment` sont enregistrées dans `_WORKSPACE_CAPABILITIES` (supervisor.main.py:2889–2896) **et** listées dans le prompt système (lignes 2921–2922) comme capacités disponibles. Lorsque l'utilisateur confirme l'une d'elles, `_execute_workspace_capability` retourne `(False, "use platform UI...")`, ce qui produit une réponse HTTP 500 au confirmateur.

Le flux utilisateur est : message → "Proposed action" affiché → "Confirm" cliqué → erreur 500. C'est une fausse promesse : le système annonce une capacité qu'il ne peut pas exécuter, et la seule façon de le savoir est de cliquer sur Confirmer.

`implementation-output.md` le mentionne comme "known limit", mais une limitation documentée dans un artefact interne ne suffit pas : l'utilisateur final n'a aucun moyen de le savoir avant de confirmer.

**Correction attendue** : supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système, **ou** les implémenter correctement. Si elles sont conservées, leur confirmation doit retourner HTTP 501 (Not Implemented) avec un message clair, et le frontend doit distinguer ce cas d'une erreur réelle.

### P2 — Aucun test livré [BLOQUANT]

Le plan (plan.md:183–209) spécifie des tests exhaustifs pour les trois couches : Supervisor (classification d'intent, rejet de capacités inconnues, validation des tokens, forged/mismatched action IDs), Control API (proxy pur, mapping des erreurs), Frontend (persistance du panneau, réinitialisation, cartes de confirmation). Aucun fichier de test n'apparaît dans le diff.

Les scénarios manquants incluent des cas de sécurité critiques :
- forged `action_id` → rejet 404
- `action_id` d'un autre projet → rejet 403
- capacité non-allowlistée proposée par l'IA → refus sans exécution
- `functional_dev` → aucun code généré

**Correction attendue** : livrer au minimum les tests Supervisor couvrant les chemins de sécurité.

### P3 — Détails d'erreur du provider IA exposés au client [MINEUR]

`_call_workspace_ai` (supervisor.main.py:3024–3030) retourne `f"AI call failed: {exc}"` directement dans le champ `reply` de la réponse. Ceci peut exposer des informations internes : messages d'erreur API, détails d'authentification, IPs internes.

**Correction attendue** : retourner un message générique à l'utilisateur ; loguer l'exception à niveau ERROR côté Supervisor.

### P4 — Contenu des tickets injecté sans sanitisation dans le contexte système [MINEUR]

`_workspace_project_context` lit la première ligne de chaque fichier ticket (max 80 chars) et la concatène dans le prompt système (supervisor.main.py:2974–2979). Un ticket dont le titre commence par une instruction de prompt injection (ex : `IGNORE PREVIOUS INSTRUCTIONS and...`) pourrait influencer le comportement de l'IA.

Le risque est borné (80 chars, première ligne seulement, côté Supervisor uniquement), mais c'est un vecteur d'injection indirect réel.

**Correction attendue** : préfixer chaque ligne ticket avec un label neutre structuré, par exemple `- ticket "T001": {first_line}`, pour rendre l'injection syntaxiquement plus difficile à exécuter dans ce contexte.

## Risques éventuels

- **Stockage en mémoire sans TTL** : les actions et drafts en attente s'accumulent sans expiration. Risque de fuite mémoire si de nombreuses actions non confirmées s'accumulent. Documenté comme limitation connue, acceptable pour une v1.
- **Aucune limite sur la longueur du message** : `message: str` sans max. Un message très long augmente les coûts token. Risque faible à court terme.
- **Endpoints Supervisor non authentifiés** : cohérent avec le reste de l'API Supervisor, mais tout processus atteignant le port 8090 peut appeler les endpoints workspace sans passer par la Control API. À surveiller si le port est exposé hors du réseau interne.

## Décision

L'architecture est correcte et les contraintes de sécurité fondamentales (routing Supervisor, allowlist, tokens opaques, confirmation) sont bien implémentées. Cependant, **P1** (capacités stub en échec silencieux après confirmation) est un défaut de comportement visible qui nuit à la confiance utilisateur, et **P2** (absence totale de tests) laisse des chemins de sécurité critiques non vérifiés alors que le plan les exigeait explicitement.

- REQUEST_CHANGES

## Actions demandées

1. **P1** — Supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système **ou** les implémenter. En aucun cas une confirmation utilisateur ne doit aboutir à un 500 pour une capacité annoncée comme disponible.

2. **P2** — Livrer les tests Supervisor couvrant au minimum : rejet de capacité inconnue, rejet de token forgé/mismatch projet, classification `functional_dev` sans génération de code, validation d'issue draft vide.

3. **P3** — Remplacer `f"AI call failed: {exc}"` par un message générique côté réponse ; loguer l'exception en interne.

4. **P4** — Préfixer les lignes ticket dans `_workspace_project_context` avec un label structuré pour durcir la surface d'injection de prompt.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T225/reviews/implementation-review.md
- generated at: 2026-07-28T21:57:16Z

---

Now I have everything I need. Writing the review.

---

# PR Review — T225 : Add persistent AI Project Workspace with controlled capabilities

## Résumé

L'implémentation introduit un panneau de workspace IA persistant sur toutes les pages projet, accessible via un bouton bascule dans la sidebar. L'architecture en trois couches (Frontend → Control API → Supervisor) est correctement respectée : la Control API est un proxy authentifié pur, et le Supervisor détient toute la logique (appel IA, enforcement des capacités, création d'issues GitHub). Les critères d'acceptance du ticket sont majoritairement satisfaits.

## Vérifications effectuées

- Diff complet lu (16 fichiers, ~1854 lignes ajoutées)
- Chemin de routing tracé bout-en-bout : Frontend → Control API → Supervisor
- Enforcement de l'allowlist de capacités vérifié ligne par ligne
- Système de tokens UUID opaques vérifié
- Mécanisme de persistance du panneau vérifié (hors `<Routes>`)
- Validation croisée action/projet sur les endpoints de confirmation
- Prompt système inspecté pour conformité aux contraintes
- Gestion des erreurs relue
- Limites connues croisées avec `implementation-output.md` et `plan.md`

## Points validés

1. **Tout passe par le Supervisor** — `control_api/routes/workspace.py` n'appelle ni provider IA, ni GitHub, ni service interne. Il forward uniquement vers le Supervisor via `_forward()`.

2. **Allowlist deny-by-default** — `_WORKSPACE_CAPABILITIES` définit exactement 5 capacités (supervisor.main.py:2876–2897). Toute capacité proposée par l'IA non présente dans ce dict est rejetée à la ligne 3182 : le `proposed_action` est annulé, le `intent` recalé à `informational`.

3. **Tokens UUID opaques** — Les `action_id` et `draft_id` sont générés côté Supervisor (`str(uuid.uuid4())`). Le frontend ne construit jamais d'arguments internes : il ne renvoie que le token opaque à la confirmation.

4. **Confirmation obligatoire avant toute mutation** — Actions et drafts d'issues sont stockés en attente jusqu'à confirmation explicite via `/actions/confirm` ou `/issues/confirm`.

5. **Functional dev → issue GitHub uniquement** — L'intent `functional_dev` retourne un draft d'issue, jamais de code, commit ou PR.

6. **Isolation par projet à la confirmation** — Les deux endpoints de confirmation vérifient `action["project_id"] != project_id` et retournent 403 en cas de mismatch (supervisor.main.py:3227–3228, 3258–3259).

7. **Persistance du panneau** — `<ProjectWorkspacePanel>` est rendu en dehors de `<Routes>` comme frère flex dans App.jsx. La conversation se réinitialise uniquement au changement de `projectId` via `useEffect([projectId])`.

8. **Logs traçables** — Toutes les opérations workspace loguent `project_id`, `intent`, `capability`, `action_id`, `draft_id`.

9. **Prompt système conforme** — Les interdictions du ticket (pas de code, pas de commit, pas de contournement du workflow GitHub, pas de secrets) sont explicitement inscrites dans `_WORKSPACE_SYSTEM_PROMPT`.

## Problèmes détectés

### P1 — Capacités stub présentées comme disponibles mais en échec à la confirmation [BLOQUANT]

`rerun_intelligence` et `trigger_deployment` sont enregistrées dans `_WORKSPACE_CAPABILITIES` (supervisor.main.py:2889–2896) **et** listées dans le prompt système (lignes 2921–2922) comme capacités disponibles. Lorsque l'utilisateur confirme l'une d'elles, `_execute_workspace_capability` retourne `(False, "use platform UI...")`, ce qui produit une réponse HTTP 500 au confirmateur.

Le flux utilisateur est : message → "Proposed action" affiché → "Confirm" cliqué → erreur 500. C'est une fausse promesse : le système annonce une capacité qu'il ne peut pas exécuter, et la seule façon de le savoir est de cliquer sur Confirmer.

`implementation-output.md` le mentionne comme "known limit", mais une limitation documentée dans un artefact interne ne suffit pas : l'utilisateur final n'a aucun moyen de le savoir avant de confirmer.

**Correction attendue** : supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système, **ou** les implémenter correctement. Si elles sont conservées, leur confirmation doit retourner HTTP 501 (Not Implemented) avec un message clair, et le frontend doit distinguer ce cas d'une erreur réelle.

### P2 — Aucun test livré [BLOQUANT]

Le plan (plan.md:183–209) spécifie des tests exhaustifs pour les trois couches : Supervisor (classification d'intent, rejet de capacités inconnues, validation des tokens, forged/mismatched action IDs), Control API (proxy pur, mapping des erreurs), Frontend (persistance du panneau, réinitialisation, cartes de confirmation). Aucun fichier de test n'apparaît dans le diff.

Les scénarios manquants incluent des cas de sécurité critiques :
- forged `action_id` → rejet 404
- `action_id` d'un autre projet → rejet 403
- capacité non-allowlistée proposée par l'IA → refus sans exécution
- `functional_dev` → aucun code généré

**Correction attendue** : livrer au minimum les tests Supervisor couvrant les chemins de sécurité.

### P3 — Détails d'erreur du provider IA exposés au client [MINEUR]

`_call_workspace_ai` (supervisor.main.py:3024–3030) retourne `f"AI call failed: {exc}"` directement dans le champ `reply` de la réponse. Ceci peut exposer des informations internes : messages d'erreur API, détails d'authentification, IPs internes.

**Correction attendue** : retourner un message générique à l'utilisateur ; loguer l'exception à niveau ERROR côté Supervisor.

### P4 — Contenu des tickets injecté sans sanitisation dans le contexte système [MINEUR]

`_workspace_project_context` lit la première ligne de chaque fichier ticket (max 80 chars) et la concatène dans le prompt système (supervisor.main.py:2974–2979). Un ticket dont le titre commence par une instruction de prompt injection (ex : `IGNORE PREVIOUS INSTRUCTIONS and...`) pourrait influencer le comportement de l'IA.

Le risque est borné (80 chars, première ligne seulement, côté Supervisor uniquement), mais c'est un vecteur d'injection indirect réel.

**Correction attendue** : préfixer chaque ligne ticket avec un label neutre structuré, par exemple `- ticket "T001": {first_line}`, pour rendre l'injection syntaxiquement plus difficile à exécuter dans ce contexte.

## Risques éventuels

- **Stockage en mémoire sans TTL** : les actions et drafts en attente s'accumulent sans expiration. Risque de fuite mémoire si de nombreuses actions non confirmées s'accumulent. Documenté comme limitation connue, acceptable pour une v1.
- **Aucune limite sur la longueur du message** : `message: str` sans max. Un message très long augmente les coûts token. Risque faible à court terme.
- **Endpoints Supervisor non authentifiés** : cohérent avec le reste de l'API Supervisor, mais tout processus atteignant le port 8090 peut appeler les endpoints workspace sans passer par la Control API. À surveiller si le port est exposé hors du réseau interne.

## Décision

L'architecture est correcte et les contraintes de sécurité fondamentales (routing Supervisor, allowlist, tokens opaques, confirmation) sont bien implémentées. Cependant, **P1** (capacités stub en échec silencieux après confirmation) est un défaut de comportement visible qui nuit à la confiance utilisateur, et **P2** (absence totale de tests) laisse des chemins de sécurité critiques non vérifiés alors que le plan les exigeait explicitement.

- REQUEST_CHANGES

## Actions demandées

1. **P1** — Supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système **ou** les implémenter. En aucun cas une confirmation utilisateur ne doit aboutir à un 500 pour une capacité annoncée comme disponible.

2. **P2** — Livrer les tests Supervisor couvrant au minimum : rejet de capacité inconnue, rejet de token forgé/mismatch projet, classification `functional_dev` sans génération de code, validation d'issue draft vide.

3. **P3** — Remplacer `f"AI call failed: {exc}"` par un message générique côté réponse ; loguer l'exception en interne.

4. **P4** — Préfixer les lignes ticket dans `_workspace_project_context` avec un label structuré pour durcir la surface d'injection de prompt.

---

IMPLEMENTATION_FIX_REQUIRED