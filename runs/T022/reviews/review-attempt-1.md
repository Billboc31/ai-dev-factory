# PR Review — T022 Generic Workflow Prompts

## Résumé

Implémentation d'un mécanisme de fallback générique pour les prompts workflow. Quand aucun prompt spécifique `prompts/TXXX-{step}.md` n'existe, le système résout `prompts/generic/{step}.md` et injecte automatiquement `runs/TXXX/ticket.md` dans le contenu. Les prompts spécifiques existants restent prioritaires sans aucune modification.

## Vérifications effectuées

- Lecture du ticket T022 et du plan approuvé
- Diff complet `main...HEAD` sur `tools/agent_runner/run_step.py`
- Lecture de chacun des 5 fichiers `prompts/generic/*.md`
- Lecture de `tests/test_prompt_resolution.py` (106 lignes)
- Exécution des tests : `pytest tests/test_prompt_resolution.py -v` → **6 passed**
- Vérification de l'alignement plan ↔ implémentation

## Points validés

**Fallback resolution**
- Ordre de résolution correct : ticket-specific → generic → erreur explicite
- `prompt_candidates()` ajoute `prompts/generic/{step}.md` en dernier candidat — logique propre, sans casser les alias existants (`-reviewer.md`, `-memory.md`)
- `find_prompt()` retourne un tuple `(Path, str)` — le champ `source` discrimine les deux cas via `candidate.parent.name == "generic"`, fiable dans la structure contrôlée du projet

**Priorité des prompts spécifiques**
- `test_ticket_specific_takes_priority` : vérifié, la priorité est correcte
- Aucun ticket existant n'est impacté — tous les prompts `prompts/TXXX-*.md` continuent d'être résolus en premier

**Logs explicites**
- Chaque résolution logge `prompt: resolved={path} source={source}` dans `runtime.log`
- L'injection logge `prompt: generic fallback — injecting {ticket_md_path}`
- Format cohérent avec les entrées existantes du log runtime

**Compatibilité préservée**
- `show_next()` adapté (`prompt_path, _ = find_prompt(...)`) — impact minimal
- Aucun changement à `run_ticket.py`, `run_daemon.py`, `memory-apply`
- Pas de refactor transversal

**Tests significatifs**
- 6 cas couvrant : priorité ticket-specific, fallback générique, absence totale, logging de la source, injection de `ticket.md`, erreur si `ticket.md` manquant
- Tests isolés via `tmp_path` + `monkeypatch.chdir()` — pas de dépendance à l'état du repo
- Le plan annonçait 5 tests, 6 ont été livrés — le cas d'erreur sur `ticket.md` manquant est un ajout bienvenu

**Scope**
- 3 points modifiés dans `run_step.py`, exactement ceux prévus au plan
- 5 fichiers `prompts/generic/` créés, un par step workflow
- Hors-scope respecté : pas de génération automatique, pas de suppression de prompts, pas de GitHub/UI/daemon

## Problèmes détectés

**Import inutilisé dans les tests**
- `from io import StringIO` (ligne 4 de `test_prompt_resolution.py`) n'est jamais utilisé dans le fichier
- Mineur — n'affecte pas la correction ni les tests

## Risques éventuels

**Source detection par nom de répertoire**
- La logique `candidate.parent.name == "generic"` fonctionnerait incorrectement si un répertoire `prompts/other-generic/` était créé. Risque négligeable dans la structure actuelle, mais à documenter si l'arborescence évolue.

**Absence de test pour les alias de step**
- `review` → `-reviewer.md`, `memory-updater` → `-memory.md` : les alias fonctionnent (code inchangé) mais n'ont pas de test dédié dans ce fichier. Acceptable — les alias existaient avant ce ticket et sont couverts implicitement.

## Décision

- APPROVED

## Actions demandées

- Supprimer l'import `StringIO` inutilisé dans `tests/test_prompt_resolution.py` (non bloquant, peut être fait lors d'un prochain passage ou via PR séparée)
