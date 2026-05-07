# Plan — T002 — Lifecycle PR IA et artefacts agent

Conforme à `ai/templates/plan-template.md`. Référence ticket : `tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md`.

## Contexte

`docs/ai/workflow.md` définit le cycle métier (onze étapes) et les trois validations obligatoires avant merge (`PLAN_APPROVED`, `IMPLEMENTATION_APPROVED`, `MEMORY_APPROVED`). Il manque une spécification **GitHub-centric** : branches, contenu des PR, emplacement versionné des artefacts (`runs/TXXX/`), statuts, transitions, escalade, et répartition des responsabilités entre agent local, conversation (type ChatGPT) et humain. Le ticket T002 impose de créer `docs/ai/pr-lifecycle.md` et de standardiser l’arborescence des runs, **sans code**, sans Actions, sans API, sans outil éditeur verrouillé, sans modifier le fichier ticket.

## Objectif

Rédiger la documentation qui permet à un **agent local minimal** futur (hors périmètre de ce ticket) et aux humains de :

- appliquer **1 ticket = 1 branche = 1 PR** ;
- déposer aux **bons moments** les prompts, reviews, fixes, tests et brouillons mémoire sous `runs/TXXX/` ;
- maintenir des **statuts cohérents** alignés sur `ai/templates/workflow-status-template.md` ;
- respecter les **passages d’étape** (dont : pas de mise à jour de la mémoire canonique avant `IMPLEMENTATION_APPROVED`) ;
- appliquer les **règles d’escalade** cohérentes avec `workflow.md` et les niveaux de risque.

## Fichiers concernés

| Fichier | Action |
|---------|--------|
| `docs/ai/pr-lifecycle.md` | **Créer** — document principal ; structure cible détaillée ci-dessous (à recopier en sections dans le fichier final). |
| `docs/ai/workflow.md` | **Modifier** (optionnel, recommandé) — ajouter en tête ou en fin une phrase + lien : « Détails GitHub, branches, PR et `runs/` : `pr-lifecycle.md`. » pour éviter la divergence. |
| `docs/ai/global-context.md` | **Modifier** (optionnel) — une ligne pointant vers `pr-lifecycle.md` si on centralise la « source de vérité workflow côté GitHub ». |
| `ai/templates/workflow-status-template.md` | **Référencer** depuis `pr-lifecycle.md` ; pas d’obligation de le changer. |
| `ai/templates/fix-prompt-template.md` | **Référencer** pour les fix prompts dans `runs/TXXX/fixes/`. |
| `runs/T002/plan.md` | **Créé** — ce fichier. |
| `tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md` | **Ne pas modifier** (contrainte). |

### Structure cible de `docs/ai/pr-lifecycle.md`

Ordre de sections suggéré pour le fichier à rédiger :

1. **Introduction** — Rôle du doc ; lien vers `workflow.md` (sémantique métier) vs ce doc (GitHub + artefacts).
2. **Identité PR** — 1 ticket = 1 branche = 1 PR ; la PR est le canal de communication entre agents ; le repo reste la source de vérité.
3. **Conventions de branches** — Préfixe recommandé (ex. `ticket/T002-...` ou `T002-...`) ; une branche par ticket ; pas de branche « fourre-tout » multi-tickets.
4. **Conventions de PR** — Titre et description (référence `TXXX`, lien vers fichier ticket) ; checklist des trois gates dans le corps ; où se trouve l’état courant (voir section 5).
5. **Statut workflow** — Les six statuts (`PLAN_APPROVED`, `PLAN_FIX_REQUIRED`, `IMPLEMENTATION_APPROVED`, `IMPLEMENTATION_FIX_REQUIRED`, `MEMORY_APPROVED`, `MEMORY_FIX_REQUIRED`) ; préciser qu’ils s’appliquent **par gate** (plan / implémentation / mémoire) ; **fichier versionné** recommandé : `runs/TXXX/workflow-status.md` initialisé depuis `ai/templates/workflow-status-template.md` ; commentaire PR optionnel en miroir, jamais seule source de vérité.
6. **Arborescence `runs/TXXX/`** — Détails dans la section « Étapes » ci-dessous (à développer dans `pr-lifecycle.md`).
7. **Cycle étape par étape** — Tableau : étape workflow → artefacts produits → condition de passage suivante.
8. **Fix prompts** — Emplacement `runs/TXXX/fixes/` ; nommage itératif (`fix-01-*.md`) ; chaînage selon statut `*_FIX_REQUIRED`.
9. **Mémoire** — Distinguer `runs/TXXX/memory/` (brouillons / propositions de diff) de `docs/ai/global-context.md`, `project-life.md`, `decisions-log.md` (mémoire **canonique** uniquement après processus validé et gate mémoire).
10. **Responsabilités** — Agent local / conversation / humain (voir section dédiée dans les Étapes).
11. **Escalade et risque** — Lien avec `CHAT_REVIEW_REQUIRED`, `HIGH_RISK`, section escalade de `workflow.md`.
12. **Agent local minimal** — Capacités attendues et garde-fous (voir Étapes).

## Étapes

1. **Rédiger `docs/ai/pr-lifecycle.md`** en suivant la structure cible ci-dessus, avec le même vocabulaire que `workflow.md`.

2. **Conventions de branches** — Documenter : nommage ; création depuis la branche de base du projet (ex. `main`) ; durée de vie = durée du ticket jusqu’au merge.

3. **Conventions de PR** — Documenter : lien ticket ; labels optionnels génériques ; interdiction de merge sans les trois `*_APPROVED` ; pas de merge automatique.

4. **Statuts** — Expliquer la machine d’état logique : après plan review → soit `PLAN_APPROVED` soit `PLAN_FIX_REQUIRED` ; après implémentation review → soit `IMPLEMENTATION_APPROVED` soit `IMPLEMENTATION_FIX_REQUIRED` ; après memory review → soit `MEMORY_APPROVED` soit `MEMORY_FIX_REQUIRED`. Un seul « gate » actif à la fois pour simplifier l’agent minimal.

5. **Structure `runs/TXXX/`** — Définir précisément :
   - `prompts/` — prompts par rôle ou par étape (ex. `planner.md`, `coder.md`, alignés avec `prompts/TXXX-*.md` à la racine si on duplique ou référence : le doc doit trancher « copie dans le run » vs « lien vers `prompts/` » pour éviter la double maintenance ; recommandation : **référencer** les prompts canoniques sous `prompts/` et n’utiliser `runs/.../prompts/` que pour des variantes ou traces d’exécution si besoin).
   - `reviews/` — `plan-review.md`, `implementation-review.md`, `memory-review.md` (noms conventionnels).
   - `fixes/` — fix prompts structurés, numérotation si boucles.
   - `tests/` — commandes reproductibles, résultats, logs textuels.
   - `memory/` — propositions de modification mémoire avant application dans `docs/ai/`.

6. **Conditions de passage entre étapes** — Pour chaque transition : prérequis explicites (ex. Coder uniquement si `PLAN_APPROVED` ; Memory updater uniquement si `IMPLEMENTATION_APPROVED` ; merge uniquement si `MEMORY_APPROVED`).

7. **Responsabilités** — Rédiger un tableau ou trois sous-sections :
   - **Agent local** — Création branche/PR, dossiers `runs/`, écriture fichiers, mise à jour `workflow-status.md`, application des prompts versionnés ; **ne merge pas** ; **ne lance pas** de CI agentique obligatoire ; **n’appelle pas** d’API LLM dans ce cadre documentaire.
   - **Conversation (ex. ChatGPT)** — Plan review, reviews CHAT, rédaction ou affinage de fix prompts, arbitrages quand le ticket est `CHAT_REVIEW_REQUIRED` ou ambigu.
   - **Humain** — Merge, validation finale `HIGH_RISK`, clarification produit, override exceptionnel **documenté** dans la PR.

8. **Règles d’escalade** — Reprendre et pointer vers `workflow.md` (workflow global, mémoire globale, architecture, multi-composants, automatisation autonome, ambiguïté) ; `HIGH_RISK` → toujours supervision humaine ou review documentée ; règle de fallback « le plus sûr ».

9. **Impacts agent local minimal** — Liste des primitives attendues : fs, git, GitHub API ou CLI (hors scope d’implémentation ici mais mentionné comme besoin futur), lecture des templates ; liste des **non-objectifs** : merge auto, Actions, API keys dans le repo.

10. **Liens transverses** — Ajouter liens vers `workflow.md`, `global-context.md`, templates statut et fix.

11. **Revue** — Vérifier les critères d’acceptation du ticket T002 (section ci-dessous).

## Risques

- **Double source de vérité** si les statuts ne vivent qu’en commentaire PR.
- **Confusion mémoire** entre `runs/.../memory/` et fichiers canoniques `docs/ai/` — à trancher clairement dans `pr-lifecycle.md`.
- **Scope creep** : documenter CI, hooks ou implémentation d’agent dans `pr-lifecycle.md` au-delà du besoin.
- **Divergence** entre `workflow.md` et `pr-lifecycle.md` si les deux sont modifiés sans lien croisé.

## Hors scope

- Implémentation d’un agent local, intégration API, GitHub Actions, merge automatique.
- Modification du fichier ticket T002.
- doc-platform / RAG.
- Dépendance à Cursor, Claude, Codex ou OpenAI API dans le contenu du lifecycle.

## Vérifications prévues

- Un lecteur peut enchaîner les étapes avec seulement `workflow.md` + `pr-lifecycle.md` + un exemple fictif `runs/T999/` décrit en annexe dans `pr-lifecycle.md` (optionnel).
- Cohérence stricte des noms de statuts avec `ai/templates/workflow-status-template.md`.
- Les trois reviews obligatoires sont visibles dans la checklist PR et dans le cycle documenté.

## Critères d’acceptation

1. `docs/ai/pr-lifecycle.md` existe et décrit le **lifecycle PR** aligné sur les **onze étapes** de `workflow.md` et les **trois reviews obligatoires**.
2. **Conventions de branches** et **de PR** sont écrites, génériques, sans outil propriétaire.
3. **Statuts workflow** documentés et reliés aux **conditions de passage** entre étapes.
4. **Structure `runs/TXXX/`** avec `prompts/`, `reviews/`, `fixes/`, `tests/`, `memory/` et le rôle de chaque dossier.
5. **Responsabilités** agent local / conversation (ChatGPT) / humain clarifiées.
6. **Règles d’escalade** présentes et cohérentes avec `workflow.md` et les niveaux de risque.
7. **Impacts** sur un futur agent local minimal : primitives attendues et garde-fous explicites.
8. Dépôt **prêt** pour une phase ultérieure d’implémentation d’agent sans rouvrir le fond du workflow métier.
