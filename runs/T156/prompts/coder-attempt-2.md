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


# T156 — T156 — Improve Runtime tab with running environments, URLs and access info

**Source**: GitHub Issue #162

## Description

Goal: make the Runtime tab the canonical dashboard for everything currently running locally or in sandbox environments.

Context:
The runtime infrastructure now supports isolated sandbox deployments with pretty proxy URLs, fallback ports, supervisors, healthchecks and validation artifacts. However, the UI still tends to show ports and low-level runtime details instead of clearly presenting the URLs and access information a developer needs.

Problem:
- running sandboxes/environments are not presented clearly enough
- pretty URLs are not prominent enough
- fallback ports are shown as if they were the primary access method
- it is not obvious which code/ref is currently deployed
- remote/dev testing flow is unclear
- runtime status, proxy readiness, healthcheck and smoke status are not visually summarized

Expected Runtime tab model:
- show all currently running runtime instances / sandboxes / environments
- display primary access URLs first:
  - web pretty URL
  - API pretty URL
- display fallback ports secondarily as debug info
- show project, sandbox id, ref/commit/branch if known
- show compose project name
- show runtime root and worktree path
- show status:
  - running / stopped / failed
  - proxy ready
  - healthcheck status
  - smoke status when available
- show timestamps:
  - created_at
  - started_at
  - last_checked_at
- provide actions:
  - open web URL
  - open API URL
  - copy URL
  - refresh status
  - view logs
  - stop
  - delete / cleanup

UX requirements:
- pretty URLs are the primary UI element
- fallback localhost ports are secondary/collapsible
- cards or table should be clean and readable
- failed environments should expose the failing step and link to logs/artifacts
- if validation.json exists, show its healthcheck_status, smoke_status and failing_step
- make it easy for a remote developer/tester to know what URL to open

Runtime data sources:
- current sandbox runtime directories
- sandbox metadata/state files
- validation.json when present
- proxy route information when present
- known allocated ports
- supervisor status when available

Acceptance:
- Runtime tab lists all active/running sandboxes/environments
- each item clearly shows web/API pretty URLs first
- fallback ports are still available but not primary
- user can copy/open URLs directly
- user can see which code/ref/commit was deployed when available
- health/proxy/smoke status is visible
- stop/delete/refresh actions are available
- UI remains generic and project-agnostic
- after deploying remotely, the user can verify that the expected code is served via the displayed URL

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

The diff looks right — 4 source files changed as planned. Here's a summary of what was implemented:

---

## Changes made

**`services/control_api/routes/runtime_dashboard.py`**
- Added imports: `resolve_proxy_routes_dir` (infra_service_manager), `build_sandbox_urls` (proxy_manager)
- Extended `SandboxRunSummary` with 8 new fields: `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at`
- Updated `_parse_sandbox_state()` to populate them:
  - `urls` — reads from `state.json`, falls back to `build_sandbox_urls(sandbox_id)`
  - `proxy_ready` — checks existence of `{proxy_routes_dir}/{sandbox_id}.yml`
  - `healthcheck_status`, `smoke_status`, `failing_step`, `last_checked_at` — read from `validation.json` with try/except guard (absent file → all `None`)
  - `ref` — reads `ref`/`branch`/`commit` from `state.json`
  - `created_at` — reads `created_at` key separately from `started_at`

**`apps/dashboard/src/api/runtimeDashboard.js`**
- Added `stopSandboxRun(id)` — needed for the Stop action button

**`apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`**
- Replaced flat table with `EnvironmentCard` components per sandbox
- Each card shows: pretty URLs (web + API) first with copy + open buttons, collapsible debug ports, proxy/healthcheck/smoke status chips, ref badge, failing step banner linked to logs, info row (compose/runtime/worktree/timestamps), Stop + Delete + View Logs actions with confirmation dialogs

**`apps/dashboard/src/pages/RuntimeDashboardPage.jsx`**
- Section title changed from "Sandbox Runs" to "Running Environments"

---

## Review

I now have everything needed for a thorough review. Let me write it.

---

# PR Review — T156: Improve Runtime tab with running environments

## Résumé

L'implémentation étend le Runtime tab avec une vue en cartes par sandbox, des URLs proxy comme élément primaire, et les statuts healthcheck/smoke/proxy. Le backend Pydantic est étendu de 8 champs, le composant `SandboxRunsTable.jsx` est réécrit en `EnvironmentCard`, et l'API client reçoit le `stopSandboxRun` manquant. L'ensemble est défensif, ciblé et respecte le scope du ticket.

## Vérifications effectuées

- Comparaison fichier par fichier vs. les critères d'acceptation du plan et du ticket
- Lecture complète de `SandboxRunsTable.jsx` (319 lignes), `runtime_dashboard.py` (parse logic), `runtimeDashboard.js`
- Vérification des imports backend (`resolve_proxy_routes_dir`, `build_sandbox_urls`)
- Analyse de la gestion des erreurs (try/except, fallbacks)
- Recherche de la présence ou absence d'un bouton "Refresh" dans la codebase

## Points validés

| Critère | Statut |
|---------|--------|
| `SandboxRunSummary` expose `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at` | ✅ |
| `validation.json` absent → champs `null` sans erreur (guard try/except ligne 182-189) | ✅ |
| Carte par sandbox, URLs pretty au-dessus du fold | ✅ |
| Ports dans section collapsible uniquement | ✅ |
| Bouton copy-to-clipboard par URL | ✅ |
| Chips proxy/healthcheck/smoke avec bonne couleur | ✅ |
| Banner failing_step avec lien vers logs | ✅ |
| Actions Stop, Delete, View Logs opérationnelles | ✅ |
| Render correct sur liste vide | ✅ |
| Fallback URL via `build_sandbox_urls()` si `state.json` n'a pas de champ `urls` | ✅ |
| Ajout de `stopSandboxRun` dans `runtimeDashboard.js` (nécessaire pour le bouton Stop) | ✅ |
| Aucune modification hors scope (SandboxManager, ProposalRunsTable, proxy infra) | ✅ |

## Problèmes détectés

### 🔴 Bloquant — Action "Refresh" manquante

Le ticket spécifie explicitement l'action **"refresh status"** dans la liste des actions. Le plan l'énumère dans les action buttons : `Open Web, Open API, Copy URL, **Refresh**, View Logs, Stop, Delete`.

L'implémentation n'a pas de bouton Refresh sur les cartes (`SandboxRunsTable.jsx` ligne 220-242 : uniquement View Logs, Stop, Delete). Le polling global à 5s (`usePolling(fetchSandboxRuns, 5000)`) couvre le cas d'usage automatiquement, mais l'action explicite est absente.

**Fix attendu** : Ajouter un bouton "Refresh" dans la barre d'actions de `EnvironmentCard` qui déclenche `onDeleted?.()` (qui remonte à `fetchSandboxRuns` dans la page parente). Un seul bouton suffit — pas besoin de nouvel endpoint.

```jsx
// Ligne ~226, dans la div.flex des actions
<button
  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
  onClick={() => onDeleted?.()}
>
  Refresh
</button>
```

### 🟡 Mineur — `CopyButton` sans gestion d'erreur clipboard

`navigator.clipboard.writeText` est une Promise qui peut être rejetée (contexte non-HTTPS, permission refusée). La ligne 49 n'a pas de `.catch()` — le rejet est silencieux, le bouton ne donne aucun feedback à l'utilisateur.

**Fix suggéré** :
```javascript
navigator.clipboard.writeText(text).then(() => {
  setCopied(true)
  setTimeout(() => setCopied(false), 1500)
}).catch(() => {
  // Fallback: could show an error indicator or use document.execCommand
})
```

### 🟡 Mineur — Label URL tronqué à `w-8` (32px)

La largeur fixe `w-8` pour le label de URL (ligne 119 : `<span className="text-xs text-gray-500 w-8 shrink-0 uppercase font-medium">`) peut tronquer visuellement des noms de clé plus longs que 3-4 caractères sans indiquer la troncature. Pas fonctionnel, mais peut induire en erreur.

### 🟡 Note — Déviation mineure du plan sur `runtimeDashboard.js`

Le plan déclarait "No changes needed" pour ce fichier, mais l'implémentation y a ajouté `stopSandboxRun`. Cette déviation est justifiée : sans cette fonction, le bouton Stop n'aurait pas d'appel API. C'est une correction de l'omission du plan, pas une dérive de scope.

## Risques éventuels

- **Performance** : vérification d'existence du fichier proxy route à chaque poll (5s × N sandboxes) — acceptable en usage dev, à surveiller si le nombre de sandboxes actifs devient élevé.
- **`started_at` fallback sur `created_at`** (ligne 152) : si les deux champs sont absents du `state.json`, `started_at` est `None`, ce qui désactive le calcul `uptime_seconds`. Comportement correct.

## Décision

L'implémentation est de haute qualité, défensive, et couvre ~95% du ticket. Le seul point bloquant est l'absence du bouton "Refresh" action explicitement requis par le ticket et le plan. Le fix est trivial (un bouton qui appelle `onDeleted?.()` déjà disponible).

## Actions demandées

1. **[Requis]** Ajouter un bouton "Refresh" dans les actions de `EnvironmentCard` (une ligne dans `SandboxRunsTable.jsx`)
2. **[Recommandé]** Ajouter `.catch()` dans `CopyButton.handleCopy` pour les contextes où l'API clipboard est indisponible

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T156/reviews/implementation-review.md
- generated at: 2026-05-28T19:23:15Z

---

I now have everything needed for a thorough review. Let me write it.

---

# PR Review — T156: Improve Runtime tab with running environments

## Résumé

L'implémentation étend le Runtime tab avec une vue en cartes par sandbox, des URLs proxy comme élément primaire, et les statuts healthcheck/smoke/proxy. Le backend Pydantic est étendu de 8 champs, le composant `SandboxRunsTable.jsx` est réécrit en `EnvironmentCard`, et l'API client reçoit le `stopSandboxRun` manquant. L'ensemble est défensif, ciblé et respecte le scope du ticket.

## Vérifications effectuées

- Comparaison fichier par fichier vs. les critères d'acceptation du plan et du ticket
- Lecture complète de `SandboxRunsTable.jsx` (319 lignes), `runtime_dashboard.py` (parse logic), `runtimeDashboard.js`
- Vérification des imports backend (`resolve_proxy_routes_dir`, `build_sandbox_urls`)
- Analyse de la gestion des erreurs (try/except, fallbacks)
- Recherche de la présence ou absence d'un bouton "Refresh" dans la codebase

## Points validés

| Critère | Statut |
|---------|--------|
| `SandboxRunSummary` expose `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at` | ✅ |
| `validation.json` absent → champs `null` sans erreur (guard try/except ligne 182-189) | ✅ |
| Carte par sandbox, URLs pretty au-dessus du fold | ✅ |
| Ports dans section collapsible uniquement | ✅ |
| Bouton copy-to-clipboard par URL | ✅ |
| Chips proxy/healthcheck/smoke avec bonne couleur | ✅ |
| Banner failing_step avec lien vers logs | ✅ |
| Actions Stop, Delete, View Logs opérationnelles | ✅ |
| Render correct sur liste vide | ✅ |
| Fallback URL via `build_sandbox_urls()` si `state.json` n'a pas de champ `urls` | ✅ |
| Ajout de `stopSandboxRun` dans `runtimeDashboard.js` (nécessaire pour le bouton Stop) | ✅ |
| Aucune modification hors scope (SandboxManager, ProposalRunsTable, proxy infra) | ✅ |

## Problèmes détectés

### 🔴 Bloquant — Action "Refresh" manquante

Le ticket spécifie explicitement l'action **"refresh status"** dans la liste des actions. Le plan l'énumère dans les action buttons : `Open Web, Open API, Copy URL, **Refresh**, View Logs, Stop, Delete`.

L'implémentation n'a pas de bouton Refresh sur les cartes (`SandboxRunsTable.jsx` ligne 220-242 : uniquement View Logs, Stop, Delete). Le polling global à 5s (`usePolling(fetchSandboxRuns, 5000)`) couvre le cas d'usage automatiquement, mais l'action explicite est absente.

**Fix attendu** : Ajouter un bouton "Refresh" dans la barre d'actions de `EnvironmentCard` qui déclenche `onDeleted?.()` (qui remonte à `fetchSandboxRuns` dans la page parente). Un seul bouton suffit — pas besoin de nouvel endpoint.

```jsx
// Ligne ~226, dans la div.flex des actions
<button
  className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
  onClick={() => onDeleted?.()}
>
  Refresh
</button>
```

### 🟡 Mineur — `CopyButton` sans gestion d'erreur clipboard

`navigator.clipboard.writeText` est une Promise qui peut être rejetée (contexte non-HTTPS, permission refusée). La ligne 49 n'a pas de `.catch()` — le rejet est silencieux, le bouton ne donne aucun feedback à l'utilisateur.

**Fix suggéré** :
```javascript
navigator.clipboard.writeText(text).then(() => {
  setCopied(true)
  setTimeout(() => setCopied(false), 1500)
}).catch(() => {
  // Fallback: could show an error indicator or use document.execCommand
})
```

### 🟡 Mineur — Label URL tronqué à `w-8` (32px)

La largeur fixe `w-8` pour le label de URL (ligne 119 : `<span className="text-xs text-gray-500 w-8 shrink-0 uppercase font-medium">`) peut tronquer visuellement des noms de clé plus longs que 3-4 caractères sans indiquer la troncature. Pas fonctionnel, mais peut induire en erreur.

### 🟡 Note — Déviation mineure du plan sur `runtimeDashboard.js`

Le plan déclarait "No changes needed" pour ce fichier, mais l'implémentation y a ajouté `stopSandboxRun`. Cette déviation est justifiée : sans cette fonction, le bouton Stop n'aurait pas d'appel API. C'est une correction de l'omission du plan, pas une dérive de scope.

## Risques éventuels

- **Performance** : vérification d'existence du fichier proxy route à chaque poll (5s × N sandboxes) — acceptable en usage dev, à surveiller si le nombre de sandboxes actifs devient élevé.
- **`started_at` fallback sur `created_at`** (ligne 152) : si les deux champs sont absents du `state.json`, `started_at` est `None`, ce qui désactive le calcul `uptime_seconds`. Comportement correct.

## Décision

L'implémentation est de haute qualité, défensive, et couvre ~95% du ticket. Le seul point bloquant est l'absence du bouton "Refresh" action explicitement requis par le ticket et le plan. Le fix est trivial (un bouton qui appelle `onDeleted?.()` déjà disponible).

## Actions demandées

1. **[Requis]** Ajouter un bouton "Refresh" dans les actions de `EnvironmentCard` (une ligne dans `SandboxRunsTable.jsx`)
2. **[Recommandé]** Ajouter `.catch()` dans `CopyButton.handleCopy` pour les contextes où l'API clipboard est indisponible

---

IMPLEMENTATION_FIX_REQUIRED