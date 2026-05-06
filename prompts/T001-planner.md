# Prompt Planner — T001

Rôle : Planner

Lis attentivement :
- docs/ai/global-context.md
- docs/ai/workflow.md
- docs/ai/project-life.md
- ai/roles/planner.md
- ai/skills/architecture-discipline.md
- ai/skills/code-quality.md
- ai/skills/documentation.md
- ai/skills/refactor-safety.md
- ai/templates/plan-template.md
- GitHub Issue T001
- Le repository source `Billboc31/ai-dev-team` si accessible

## Objectif

Produire un plan d’exécution pour auditer `ai-dev-team` et extraire un socle générique vers `ai-dev-factory`.

## Contraintes

- ne pas coder
- ne pas modifier le ticket
- ne pas dépendre du projet RAG/doc-platform
- ne pas migrer de logique métier spécifique
- conserver la philosophie actuelle : ticket → planner → review plan → coder → reviewer/tester → review implémentation → memory updater → review mémoire
- PR GitHub = protocole de communication entre agents
- mémoire versionnée = source de vérité long terme

## À produire

Un plan structuré conforme à `ai/templates/plan-template.md`.

Le plan doit préciser :

- quels éléments de `ai-dev-team` sont génériques
- quels éléments sont spécifiques à doc-platform/RAG et doivent être exclus
- structure cible de `ai-dev-factory`
- fichiers à créer ou modifier
- stratégie de migration minimale
- stratégie mémoire : `global-context.md`, `project-life.md`, `decisions-log.md`
- lifecycle PR IA
- règles de classification AUTO_SAFE / CHAT_REVIEW_REQUIRED / HIGH_RISK
- risques
- critères d’acceptation

## Ne fais pas

- pas d’implémentation
- pas de refactor massif
- pas d’automatisation avancée dans ce ticket
- pas de dépendance à Cursor, Claude, Codex ou OpenAI API dans le socle documentaire
