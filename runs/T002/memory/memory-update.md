# Memory Update

## Ticket

T002 — Définir le lifecycle PR IA et la structure standard des artefacts agent (`tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md`).

## Résumé des changements

- Ajout du document **`docs/ai/pr-lifecycle.md`** : lifecycle PR IA générique aligné sur `workflow.md` (sans le modifier).
- Standardisation de l’arborescence **`runs/TXXX/`** : `plan.md`, `workflow-status.md`, `prompts/`, `reviews/`, `fixes/`, `tests/`, `memory/` (extensions cohérentes par rapport au squelette minimal du ticket).
- Clarification **prompts canoniques** (`prompts/TXXX-*.md`, maintenus hors agent local) vs **snapshots** optionnels (`runs/TXXX/prompts/`).
- Artéfacts de traçabilité T002 : `runs/T002/plan.md`, `runs/T002/reviews/review.md`, `runs/T002/tests/test-report.md`, ce fichier.

## Décisions prises

- Source de vérité **opérationnelle GitHub** (branches, PR, fichiers dans `runs/`, statuts) : **`pr-lifecycle.md`**.
- **`workflow.md`** reste la source de vérité **métier** (étapes, rôles, invariants, statuts nommés) — inchangé dans le cadre T002.
- L’agent local **ne modifie pas** les prompts sous `prompts/` ; il peut écrire sous `runs/TXXX/` uniquement.

## Impacts architecture

- **Documentation uniquement** : pas de module code ni de dépendance nouvelle. L’architecture cible « agent local minimal » dispose d’une spécification fichier/PR/répertoires réutilisable.
- Le fichier **`docs/ai/decisions-log.md`** est créé pour honorer la mémoire canonique décrite dans `workflow.md` / `global-context.md` (il manquait malgré les références).

## Limitations connues

- Pas de lien depuis `workflow.md` vers `pr-lifecycle.md` (contrainte de ne pas modifier le workflow officiel) ; la navigation passe par `global-context.md` ou l’exploration du dépôt.
- Le tableau des transitions dans `pr-lifecycle.md` ne détaille pas chaque étape 1–11 ; le détail reste dans `workflow.md`.

## Dette technique

- **Mineure** : onboarding — guider les nouveaux contributeurs vers `pr-lifecycle.md` (déjà lié depuis `global-context.md`).
- Aucune dette runtime (pas de code livré).

## Prochains sujets liés

- Implémentation d’un **agent local minimal** conforme à `pr-lifecycle.md`.
- Ticket T001 / extraction depuis `ai-dev-team` (toujours dans `project-life` — Next Topics).

## Fichiers mémoire modifiés

- `docs/ai/project-life.md` — état courant, décisions T002, next topics, dette connue.
- `docs/ai/decisions-log.md` — **créé** ; entrée datée 2026-05-07 pour T002.
