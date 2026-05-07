# Project Life — ai-dev-factory

## Current State

Repository bootstrap en cours.

T002 (lifecycle PR IA et artefacts `runs/TXXX/`) est livré et sert désormais de protocole GitHub officiel.

T003 (agent local minimal) est livré.

T004 (state machine locale minimale) est livré.

T005 (external command execution) est livré.

T006 (sequential ticket runner) est livré.

T007 (git ticket branch workflow) est maintenant livré.

Artefacts T002 disponibles :
- `runs/T002/plan.md`
- `runs/T002/reviews/review.md`
- `runs/T002/tests/test-report.md`
- `runs/T002/memory/memory-update.md`

Composants disponibles :
- `tools/agent_runner/run_step.py`
- `tools/agent_runner/run_ticket.py`
- `tools/agent_runner/README.md`
- prompts T003/T007
- structures `runs/TXXX/`
- state machine workflow minimale
- exécution externe contrôlée
- workflow Git ticket branch

Le runner local minimal sait désormais :
- créer automatiquement `runs/TXXX/`
- créer les sous-dossiers standards
- résoudre les prompts canoniques
- afficher un prompt
- écrire des artefacts depuis stdin
- maintenir `workflow-status.md`
- déterminer la prochaine étape d’un ticket
- afficher le prochain prompt attendu
- afficher le prochain artefact attendu
- exécuter une commande externe explicite
- créer/switch une branche ticket
- commit les changements
- push explicitement une branche ticket
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
- T004 introduit une state machine locale simple basée sur `workflow-status.md`.
- T005 introduit l’exécution externe contrôlée via stdin/stdout.
- T007 introduit le workflow Git ticket branch (`ticket/TXXX-*`).

## Next Topics

- review distante automatique
- orchestration automatique réelle des étapes
- watcher GitHub local
- intégration LLM future
- pipeline mémoire automatisé
- extraction/migration depuis ai-dev-team

## Dette / limitations connues

- Pas encore de review distante automatique.
- Pas encore d’exécution full-auto multi-étapes.
- Aucun appel API LLM direct.
- Aucun merge automatique.
- Aucun watcher GitHub.
- Aucun système multi-agent avancé.
- State machine volontairement simplifiée.
