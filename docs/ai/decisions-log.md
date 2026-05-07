# Decisions log — ai-dev-factory

Décisions structurantes datées. Les détails opérationnels vivent dans `docs/ai/project-life.md` et les documents référencés.

---

## 2026-05-07 — T002 — Document canonique lifecycle PR et artefacts `runs/`

**Contexte** : besoin de standardiser le lifecycle des PR IA et l’arborescence des artefacts avant un agent local minimal.

**Décision** : adopter **`docs/ai/pr-lifecycle.md`** comme référence principale pour branches, PR, structure `runs/TXXX/`, statuts versionnés, séparation prompts canoniques (`prompts/TXXX-*.md`) / snapshots (`runs/TXXX/prompts/`), responsabilités (agent local / conversation / humain) et escalade (renvoi à `workflow.md`). Ne pas modifier **`docs/ai/workflow.md`** pour ce livrable.

**Conséquences** : les contributeurs et futurs agents s’appuient sur `pr-lifecycle.md` pour l’implémentation concrète côté GitHub ; la sémantique des gates et des rôles reste dans `workflow.md`.

**Références** : ticket `tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md` ; `runs/T002/reviews/review.md` (APPROVED) ; `runs/T002/tests/test-report.md` (validation) ; `runs/T002/memory/memory-update.md` (synthèse mémoire validée).
