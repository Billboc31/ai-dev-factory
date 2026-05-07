# Lifecycle PR IA — ai-dev-factory

## Rôle de ce document

Ce fichier est la **référence principale** pour le cycle de vie côté **GitHub** : branches, pull requests, emplacement des artefacts sous `runs/TXXX/`, statuts versionnés, prompts (canoniques vs snapshots), responsabilités et escalade opérationnelle.

La **sémantique métier** du pipeline (étapes, rôles, invariants, mémoire canonique) reste dans [`workflow.md`](./workflow.md). On évite d’y recopier longuement des règles déjà décrites : en cas de doute sur le *quoi* métier, se référer à `workflow.md` ; pour le *où* et le *comment* côté repo et PR, se référer à ce document.

**GitHub** reste la source de vérité du workflow (branches, PR, historique). Aucune intégration API, aucune GitHub Action et aucun agent local ne sont requis par ce document : il décrit uniquement les conventions.

---

## Prompts canoniques et snapshots d’exécution

### Prompts canoniques — `prompts/TXXX-*.md`

- Emplacement : répertoire **`prompts/`** à la racine du repo, fichiers nommés par convention **`TXXX-<rôle ou étape>.md`** (ex. `T002-planner.md`).
- Statut : **source de vérité** pour les instructions réutilisables d’un ticket ; rédigés ou maintenus typiquement via une conversation (ex. ChatGPT) puis **versionnés** dans le dépôt.
- Toute évolution du texte d’un prompt canonique se fait **hors** `runs/` (édition directe sous `prompts/` dans une PR dédiée ou dans le cadre du ticket concerné).

### Snapshots optionnels — `runs/TXXX/prompts/`

- Emplacement : **`runs/TXXX/prompts/`** pour un ticket donné.
- Statut : **facultatif** — copies ou traces d’exécution produites par un **agent local** (horloge, contexte injecté, sortie intermédiaire, etc.).
- **Objectif** : auditabilité et reproductibilité locale **sans** créer une seconde définition « officielle » du prompt.

### Règles pour éviter la double maintenance

1. Les **prompts canoniques** vivent **uniquement** sous **`prompts/`**.
2. Les fichiers sous **`runs/TXXX/prompts/`** ne remplacent pas les canoniques : ce sont des **snapshots** ou annexes, optionnels.
3. L’**agent local** ne doit **pas** modifier les fichiers sous **`prompts/`** ; il lit les canoniques et écrit éventuellement dans **`runs/TXXX/`** uniquement.

---

## Identité PR

- **1 ticket = 1 branche = 1 PR** (aligné sur [`workflow.md`](./workflow.md) — section Convention GitHub).
- La **PR** est le canal de communication entre agents (commentaires, fichiers versionnés, reviews).
- Le **dépôt** reste la source de vérité : tout artefact durable doit apparaître dans un commit de la branche du ticket.

---

## Conventions de branches

- Nommage recommandé : préfixe ticket, ex. `T002-pr-lifecycle` ou `ticket/T002-pr-lifecycle`.
- Une branche par ticket ; pas de branche partagée pour plusieurs tickets.
- Branche créée depuis la branche de base du projet (souvent `main`) ; vivante jusqu’au merge de la PR associée.

---

## Conventions de PR

- **Titre** : inclure l’identifiant ticket (ex. `T002 — lifecycle PR IA`).
- **Description** : lien vers le fichier ticket (ex. `tickets/TODO/T002-....md`) ; résumé court des changements.
- **Checklist** des trois gates obligatoires avant merge :
  - `PLAN_APPROVED`
  - `IMPLEMENTATION_APPROVED`
  - `MEMORY_APPROVED`
- **Merge** : réservé à l’humain ; pas de merge automatique documenté ici.

---

## Statut workflow versionné

Les statuts sont ceux de [`workflow.md`](./workflow.md) (Plan / Implémentation / Mémoire) :

- `PLAN_APPROVED` | `PLAN_FIX_REQUIRED`
- `IMPLEMENTATION_APPROVED` | `IMPLEMENTATION_FIX_REQUIRED`
- `MEMORY_APPROVED` | `MEMORY_FIX_REQUIRED`

**Recommandation** : maintenir un fichier **`runs/TXXX/workflow-status.md`** dans la branche du ticket, initialisé ou aligné sur [`ai/templates/workflow-status-template.md`](../ai/templates/workflow-status-template.md). C’est la **source de vérité préférée** pour l’état courant des gates (reproductible dans le diff).

Un commentaire sur la PR peut refléter le même état ; il ne doit **pas** être la seule trace si le fichier versionné est absent.

Logique simplifiée : un **gate** actif à la fois (plan → implémentation → mémoire) ; après chaque review, soit `*_APPROVED`, soit `*_FIX_REQUIRED` pour ce gate.

---

## Arborescence `runs/TXXX/`

Pour le ticket `TXXX` :

```text
runs/TXXX/
  plan.md                 # plan d’exécution (ex. sortie planner)
  workflow-status.md      # état des gates (recommandé)
  prompts/                # snapshots optionnels — voir section « Prompts canoniques »
  reviews/                # sorties des reviews (ex. plan-review.md, implementation-review.md, memory-review.md)
  fixes/                  # fix prompts (ex. fix-01-....md) — voir ai/templates/fix-prompt-template.md
  tests/                  # commandes et résultats reproductibles
  memory/                 # brouillons mémoire avant application dans docs/ai/
```

Les **fix prompts** sous `fixes/` suivent la discipline de [`workflow.md`](./workflow.md) ; gabarit : [`ai/templates/fix-prompt-template.md`](../ai/templates/fix-prompt-template.md).

### Structure des reviews (`reviews/`)

Fichiers versionnés typiques (noms indicatifs, à adapter au projet si besoin) :

| Fichier | Moment |
|---------|--------|
| `plan-review.md` | Après plan review (gate plan) |
| `implementation-review.md` | Après reviewer / tester / implementation review (gate implémentation) |
| `memory-review.md` | Après memory review (gate mémoire) |

### Structure des fix prompts (`fixes/`)

- Un fichier par boucle de correction ou par lot logique : ex. `fix-01-plan-scope.md`, `fix-02-implementation-tests.md`.
- Contenu aligné sur [`ai/templates/fix-prompt-template.md`](../ai/templates/fix-prompt-template.md) ; stockage **versionné** dans la branche du ticket (pas seulement en commentaire PR).

### Structure des prompts (rappel)

- **Canoniques** : uniquement sous `prompts/TXXX-*.md` (voir section dédiée ci-dessus).
- **Snapshots d’exécution** : optionnellement sous `runs/TXXX/prompts/`, sans dupliquer la définition officielle.

---

## Mémoire : run vs canonique

- **`runs/TXXX/memory/`** : propositions, brouillons ou extraits préparés par le Memory Updater **avant** validation mémoire.
- **`docs/ai/global-context.md`**, **`project-life.md`**, **`decisions-log.md`** : mémoire **canonique**. Elle n’est mise à jour qu’après **`IMPLEMENTATION_APPROVED`**, puis review mémoire, comme dans `workflow.md`.

---

## Cycle étape par étape (rappel opérationnel)

Les onze étapes sont définies dans [`workflow.md`](./workflow.md). Côté PR / fichiers :

| Transition | Condition minimale |
|------------|---------------------|
| Écrire du code | `PLAN_APPROVED` |
| Memory updater sur mémoire canonique | `IMPLEMENTATION_APPROVED` |
| Merge | `PLAN_APPROVED` **et** `IMPLEMENTATION_APPROVED` **et** `MEMORY_APPROVED` |

En cas de refus : statut `*_FIX_REQUIRED`, fix prompt sous `runs/TXXX/fixes/`, puis relance du rôle concerné (`workflow.md` — Gestion des corrections).

---

## Responsabilités

| Acteur | Rôle |
|--------|------|
| **Agent local** (futur) | Branche, PR, arborescence `runs/`, mise à jour de `workflow-status.md`, lecture des prompts sous `prompts/`, écriture optionnelle sous `runs/TXXX/` (dont snapshots) ; **ne modifie pas** `prompts/TXXX-*.md` ; **ne merge pas**. |
| **Conversation (ex. ChatGPT)** | Rédaction / maintenance des **prompts canoniques** dans `prompts/`, reviews plan ou chat, fix prompts, arbitrage si `CHAT_REVIEW_REQUIRED` ou ambiguïté. |
| **Humain** | Merge, validation en `HIGH_RISK`, clarifications produit, override exceptionnel **tracé** dans la PR. |

---

## Escalade et risque

Se référer aux niveaux **AUTO_SAFE**, **CHAT_REVIEW_REQUIRED**, **HIGH_RISK** et à la section « Escalade » de [`workflow.md`](./workflow.md). `HIGH_RISK` implique toujours une supervision explicite (humain ou processus documenté). En cas de doute : règle de fallback la plus sûre (`workflow.md`).

---

## Agent local minimal — impacts (sans implémentation)

**Attendu plus tard** (hors périmètre de ce repo documentaire) : capacités type système de fichiers, git, ouverture ou mise à jour de PR via GitHub (CLI ou API), lecture des templates.

**Hors scope explicite** : merge automatique, GitHub Actions obligatoires pour le workflow IA, appels API LLM comme prérequis au document lui-même, modification des prompts canoniques sous `prompts/`.

---

## Liens utiles

- [`workflow.md`](./workflow.md) — lifecycle métier, rôles, statuts, mémoire, escalade.
- [`global-context.md`](./global-context.md) — vision et invariants (mise à jour rare).
- [`ai/templates/workflow-status-template.md`](../ai/templates/workflow-status-template.md)
- [`ai/templates/fix-prompt-template.md`](../ai/templates/fix-prompt-template.md)
