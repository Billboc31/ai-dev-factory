# Project Life — ai-dev-factory

## Current State

Repository bootstrap en cours.

T002 (lifecycle PR IA et artefacts `runs/TXXX/`) est livré et sert désormais de protocole GitHub officiel.

T003 (agent local minimal) est maintenant livré dans une première version fonctionnelle.

Artefacts T002 disponibles :
- `runs/T002/plan.md`
- `runs/T002/reviews/review.md`
- `runs/T002/tests/test-report.md`
- `runs/T002/memory/memory-update.md`

Composants T003 disponibles :
- `tools/agent_runner/run_step.py`
- `tools/agent_runner/README.md`
- prompts T003
- structure `runs/T003/`

Le runner local minimal sait désormais :
- créer automatiquement `runs/TXXX/`
- créer les sous-dossiers standards
- résoudre les prompts canoniques
- afficher un prompt
- écrire des artefacts depuis stdin
- maintenir `workflow-status.md`
- protéger les chemins dangereux

Le workflow chat-driven complet a été testé :
- ticket
- planner
- review
- memory update
- apply mémoire canonique

## Decisions

- GitHub PR devient le protocole de communication entre agents IA.
- Le système mémoire est versionné dans le repository.
- Les reviews IA intermédiaires sont obligatoires.
- Les rôles planner/coder/reviewer/tester sont conservés.
- `pr-lifecycle.md` devient la référence GitHub/workflow opérationnelle.
- `workflow.md` reste la référence métier.
- Les prompts canoniques vivent sous `prompts/`.
- Les snapshots d’exécution vivent sous `runs/TXXX/`.
- Le runner local minimal reste volontairement non autonome.
- Les prompts restent conçus par ChatGPT/conversation et non générés par l’agent.

## Next Topics

- orchestration automatique des étapes
- watcher GitHub local
- intégration LLM future
- pipeline mémoire automatisé
- reviews automatiques
- extraction/migration depuis ai-dev-team

## Dette / limitations connues

- T003 reste manuel : pas de boucle autonome.
- Aucun appel API LLM.
- Aucun merge automatique.
- Aucun watcher GitHub.
- Aucun système multi-agent avancé.
