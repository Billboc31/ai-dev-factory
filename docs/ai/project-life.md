# Project Life — ai-dev-factory

## Current State

Repository bootstrap en cours. Le ticket **T002** (lifecycle PR IA et artefacts `runs/TXXX/`) est **livré** : référence unique [`pr-lifecycle.md`](./pr-lifecycle.md), review **APPROVED**, tests **VALIDATION**.

Artefacts de traçabilité T002 : `runs/T002/plan.md`, `runs/T002/reviews/review.md`, `runs/T002/tests/test-report.md`, `runs/T002/memory/memory-update.md`.

**Impacts T002 (mémoire validée)** : documentation uniquement ; pas de module code ni de dépendance nouvelle ; spécification fichier / PR / `runs/` pour un futur agent local minimal.

## Decisions

- GitHub PR devient le protocole de communication entre agents IA.
- Le système mémoire est versionné dans le repository.
- Les reviews IA intermédiaires sont obligatoires.
- Les rôles planner/coder/reviewer/tester sont conservés.
- **T002** — La convention opérationnelle GitHub (branches, PR, `runs/TXXX/`, statuts versionnés) est documentée dans **`docs/ai/pr-lifecycle.md`** ; le workflow métier reste dans **`docs/ai/workflow.md`** (non modifié lors de T002).
- **T002** — Prompts **canoniques** : `prompts/TXXX-*.md` ; **snapshots d’exécution** optionnels : `runs/TXXX/prompts/` ; l’agent local ne modifie pas les canoniques.
- **T002** — Responsabilités documentées : agent local (fichiers, PR, `runs/`, pas merge) ; conversation (ex. prompts canoniques, reviews chat) ; humain (merge, `HIGH_RISK`).

## Next Topics

- extraction générique depuis ai-dev-team
- agent local minimal — implémentation conforme à [`pr-lifecycle.md`](./pr-lifecycle.md)
- agent mémoire
- générateur de prompts
- orchestration locale

## Dette / limitations connues

- Découverte de `pr-lifecycle.md` : pas de lien depuis `workflow.md` (contrainte de ne pas modifier le workflow officiel) ; navigation via [`global-context.md`](./global-context.md) ou exploration du dépôt.
- Le tableau des transitions dans `pr-lifecycle.md` ne détaille pas chaque étape 1–11 ; le détail reste dans [`workflow.md`](./workflow.md).
- Le journal [`decisions-log.md`](./decisions-log.md) a été amorcé avec la décision T002 (fichier absent auparavant alors que référencé dans le workflow).
- **Dette mineure (onboarding)** : guider les nouveaux contributeurs vers `pr-lifecycle.md` (déjà lié depuis `global-context.md`).
- Aucune dette runtime (pas de code livré pour T002).
