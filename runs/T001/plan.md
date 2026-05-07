# Plan — T001 — Audit ai-dev-team et extraction vers ai-dev-factory

Conforme à `ai/templates/plan-template.md`. Ticket : audit `Billboc31/ai-dev-team`, extraction d’un socle générique vers `ai-dev-factory`. GitHub Issue T001 non présente dans ce dépôt : hypothèses basées sur le prompt planner et l’arborescence publique du dépôt source.

## Contexte

`ai-dev-factory` amorce un framework générique (workflow GitHub, mémoire versionnée, rôles agents). `ai-dev-team` contient sous `docs/ai/` un socle documentaire réutilisable, mais aussi une vision produit **doc-platform / RAG** (stack, monorepo, règles rag-admin / life-rag) et une archive volumineuse `docs/archive/rag-admin/`. Le ticket impose un **audit** et une **stratégie d’extraction minimale**, sans code, sans modifier le ticket GitHub, sans migrer de logique métier ni dépendre du projet RAG.

## Objectif

Produire une feuille de route exécutable pour :

1. Classer tout le périmètre pertinent de `ai-dev-team` en **générique**, **générique après neutralisation**, ou **exclu** (RAG / doc-platform).
2. Fixer la **structure cible** de `ai-dev-factory`, les **fichiers** à créer ou adapter, et une **migration minimale**.
3. Aligner la **mémoire** (`global-context.md`, `project-life.md`, `decisions-log.md`), le **lifecycle PR IA**, et les **règles de risque** avec les invariants déjà documentés dans ce repo.

## Fichiers concernés

### Source — `Billboc31/ai-dev-team` (branche `main`, inventaire API)

**Générique (réutilisable tel quel ou après édition légère)**

| Chemin source | Notes |
|---------------|--------|
| `docs/ai/roles/coder.md`, `planner.md`, `reviewer.md`, `tester.md`, `ticket-writer.md` | Processus IA ; adapter les références de chemins si la cible utilise `ai/roles/` et non `docs/ai/roles/`. |
| `docs/ai/skills/*.md` | Transverse (architecture, code-quality, documentation, refactor-safety, debugging, git-discipline, security, testing) — comparer avec `ai/skills/` existant ; fusionner les formulations utiles sans dupliquer. |
| `docs/ai/templates/plan-template.md`, `ticket-template.md`, `pr-review-template.md`, `handoff-template.md`, `task-prompt-template.md`, `roadmap-template.md`, `architecture-template.md`, `global-context-template.md` | Génériques si placeholders projet ; éviter d’importer des formulations liées au RAG dans les templates. |
| Sections « workflow par tickets » de `docs/ai/global-context.md` | Principe ticket / plan / coder / reviewer — **ne pas** importer le reste du fichier tel quel. |

**Générique avec décision explicite**

| Chemin source | Notes |
|---------------|--------|
| `docs/ai/roles/refactorer.md` | Absent du pipeline cible factory (planner → … → memory) ; ne pas migrer tel quel, ou documenter un mapping « refactor = coder + contraintes refactor-safety » dans `decisions-log.md`. |

**Exclu — spécifique doc-platform / RAG**

| Zone | Motif |
|------|--------|
| Contenu vision/stack/architecture monorepo dans `docs/ai/global-context.md` | RAG, FastAPI, Chroma, SQLite métier, zones `services/` / `apps/` / `packages/`. |
| `docs/archive/rag-admin/**` | Tickets, plans, docs métier RAG. |
| `docs/migration/**`, `docs/reports/**` orientés RAG | Migrations et rapports produit. |
| `docs/architecture-current.md`, `docs/architecture-target.md`, `docs/monorepo-structure.md`, `docs/data-model.md`, `docs/handoff.md`, `docs/roadmap.md` | Contexte monorepo / produit sauf reclassification manuelle d’une section purement « process IA ». |

### Cible — `ai-dev-factory`

**Déjà présent**

- `docs/ai/global-context.md`, `workflow.md`, `project-life.md`
- `ai/roles/`, `ai/skills/`, `ai/templates/`
- `prompts/`, `tickets/TODO/`

**À créer ou compléter (hors implémentation code de ce ticket)**

- `docs/ai/decisions-log.md` — référencé par `workflow.md` mais absent du repo.
- `docs/ai/pr-lifecycle.md` — prévu ticket T002 ; T001 peut le mentionner comme livrable séquentiel.
- `runs/T001/plan.md` — ce fichier.

**À modifier lors de l’exécution post-audit (Coder / Memory)**

- Fichiers `ai/skills/*` ou `docs/ai/*` uniquement après revue plan et selon le diff d’audit fichier par fichier.

## Étapes

1. **Inventaire** — Lister tous les blobs sous `docs/ai/` dans `ai-dev-team` ; marquer chaque fichier : Générique / Adapter / Exclu.
2. **Diff sémantique** — Pour chaque fichier « Générique » ou « Adapter », comparer à l’équivalent `ai-dev-factory` ; conserver la version factory si elle intègre déjà le workflow à onze étapes et les trois reviews ; sinon fusionner des formulations utiles **sans** réintroduire la stack RAG.
3. **Convention de chemins** — Maintenir : mémoire et workflow dans `docs/ai/` ; rôles, skills, templates exécutables dans `ai/`. Documenter l’écart avec la source (`docs/ai/roles` → `ai/roles`) dans `project-life` ou `decisions-log` lors d’une PR d’extraction.
4. **global-context source** — Traiter comme **non importable tel quel** ; toute matière stable générique est déjà ou sera dans `docs/ai/global-context.md` factory.
5. **Templates** — Passer les templates source en revue ; exclure ou neutraliser toute référence implicite au domaine RAG.
6. **Mémoire** — Planifier création de `decisions-log.md` ; règles d’écriture : `global-context` rare, `project-life` fréquent, `decisions-log` à chaque décision structurante (cf. `workflow.md`).
7. **Lifecycle PR** — S’aligner sur la convention « 1 ticket = 1 branche = 1 PR », artefacts dans la PR / sous `runs/TXXX/` (détail : ticket T002, `docs/ai/pr-lifecycle.md`).
8. **Risque** — Consolider `ai/skills/risk-classification.md` avec les exemples de `docs/ai/workflow.md` pour une table de correspondance ticket → niveau (option documentaire post-audit).
9. **Livrable audit** — Document unique listant fichier source → décision (inclus / exclus / fusion), prêt pour une PR « extraction » incrémentale.

## Risques

- **Dérive scope** : copier `docs/archive/rag-admin` ou des plans RAG par erreur.
- **global-context** : merge mécanique avec la source réinjecte stack et règles métier rag-admin / life-rag.
- **Double vérité** : deux versions divergentes des mêmes skills entre repos.
- **Chemin `runs/T002/plan.md` dans le prompt T001** : incohérence ticket / dossier ; utiliser `runs/T001/plan.md` pour le plan T001 (ce fichier).
- **Ticket GitHub absent localement** : écart de critères si non resynchronisé avec le dépôt.

## Hors scope

- Implémentation code, refactor massif, automatisation avancée.
- Dépendances Cursor, Claude, Codex, OpenAI API dans le socle documentaire.
- Modification du ticket GitHub T001.
- Migration de logique métier ou dépendance au projet RAG/doc-platform comme contenu à porter.

## Vérifications prévues

- Chaque fichier candidat porte une **étiquette** claire (générique / exclus / adapter).
- Aucune référence résiduelle rag-admin, life-rag, Chroma, stack RAG dans les fichiers **socle** après extraction.
- Cohérence avec les trois gates : `PLAN_APPROVED`, `IMPLEMENTATION_APPROVED`, `MEMORY_APPROVED`.
- Les prompts `prompts/` continuent de pointer vers les bons chemins `ai/` et `docs/ai/`.

## Critères d’acceptation

1. **Éléments génériques** de `ai-dev-team` identifiés (au minimum tout `docs/ai/` hors contenu produit dans `global-context.md` et hors archive).
2. **Éléments exclus** listés (archive rag-admin, migrations, archi monorepo, etc.).
3. **Structure cible** `ai-dev-factory` décrite et alignée avec l’existant (`docs/ai/` + `ai/` + `prompts/` + `tickets/` + `runs/TXXX/`).
4. **Fichiers à créer ou modifier** inventoriés (dont `decisions-log.md`, futur `pr-lifecycle.md`, mises à jour skills/mémoire selon audit).
5. **Stratégie de migration minimale** : copier ou fusionner uniquement après classification ; pas de migration de logique métier.
6. **Stratégie mémoire** : rôles de `global-context.md`, `project-life.md`, `decisions-log.md` et ordre obligatoire (mémoire après `IMPLEMENTATION_APPROVED`) rappelés et appliqués dans la suite des PRs.
7. **Lifecycle PR IA** : référencé (GitHub = source de vérité, PR = bus agentique, artefacts) et renvoi explicite au ticket T002 pour la spécification détaillée.
8. **Classification AUTO_SAFE / CHAT_REVIEW_REQUIRED / HIGH_RISK** : alignée sur `docs/ai/workflow.md` et `ai/skills/risk-classification.md` ; HIGH_RISK toujours escaladé ; règle de fallback « le plus sûr » conservée.
9. **Risques** documentés (au minimum ceux listés ci-dessus).
10. **Philosophie** conservée : ticket → planner → review plan → coder → reviewer/tester → review implémentation → memory updater → review mémoire ; mémoire versionnée = vérité long terme ; PR = protocole entre agents.
