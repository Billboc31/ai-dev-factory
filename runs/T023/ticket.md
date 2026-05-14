# T023 — GitHub issue intake

## Contexte

Le workflow runtime local est maintenant capable de :

- gérer les états workflow
- exécuter planner/coder/reviewer/tester
- supporter les approvals humaines
- fonctionner avec prompts génériques
- tourner via daemon local

Mais la création des tickets runtime reste manuelle.

Le système doit maintenant pouvoir transformer une GitHub Issue en run local.

Architecture cible :

```text
GitHub Issue
→ run_issue_intake.py
→ runs/TXXX/
→ run_ticket.py
```

## Objectif

Ajouter un intake GitHub manuel capable de :

- lire une issue GitHub
- créer un run local
- créer `ticket.md`
- initialiser `state.json`
- créer la branche ticket
- préparer le workflow runtime

Le workflow réel reste exécuté par `run_ticket.py`.

## Inclus

- nouveau script `tools/agent_runner/run_issue_intake.py`
- récupération issue GitHub
- extraction titre + body
- génération `runs/TXXX/ticket.md`
- création branche ticket
- initialisation workflow
- logs explicites
- tests ciblés

## Exemple cible

```bash
python tools/agent_runner/run_issue_intake.py \
  --issue 123 \
  --ticket-id T023 \
  --branch-slug github-issue-intake
```

## Contraintes

- `run_ticket.py` reste le moteur workflow canonique
- le script intake ne doit pas gérer les transitions workflow
- le script intake ne doit pas modifier directement les états runtime après initialisation
- aucun merge automatique
- aucune PR automatique

## Hors scope

- daemon polling GitHub
- PR sync
- slash commands GitHub
- auto merge
- orchestration multi-agent
- UI web

## Critères d’acceptation

- une issue GitHub peut créer un run local
- `ticket.md` est correctement généré
- la branche ticket est créée
- `state.json` est initialisé
- les logs sont explicites
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_issue_intake.py
tests/
README.md
```
