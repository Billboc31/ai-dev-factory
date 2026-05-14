---

# PR Review — T022 Generic Workflow Prompts

## Résumé

Implémentation propre et bornée d'un mécanisme de fallback générique. Quand aucun prompt `prompts/TXXX-{step}.md` n'existe, le système résout `prompts/generic/{step}.md` et injecte `runs/TXXX/ticket.md` dans le contenu. Les prompts spécifiques restent prioritaires sans modification.

## Points validés

**Fallback resolution** — correct. `prompt_candidates()` ajoute le générique en dernier. `find_prompt()` retourne `(Path, source)`, la détection via `candidate.parent.name == "generic"` est fiable dans la structure contrôlée du projet.

**Priorité des prompts spécifiques** — vérifiée par test et par lecture du code. Aucun ticket existant impacté.

**Logs** — `prompt: resolved={path} source={source}` loggé à chaque résolution, format cohérent avec l'existant. L'injection logge également.

**Compatibilité** — `show_next()` adapté minimalement. `run_ticket.py`, `run_daemon.py`, `memory-apply` : inchangés.

**Tests** — 6/6 passent. Couvrent : priorité ticket-specific, fallback générique, absence totale, logging, injection de `ticket.md`, erreur si `ticket.md` manquant. Isolés via `tmp_path` + `monkeypatch.chdir()`.

**Scope** — exactement les 3 points prévus au plan dans `run_step.py`, plus les 5 fichiers `prompts/generic/`.

## Problème détecté

- `from io import StringIO` inutilisé ligne 4 de `test_prompt_resolution.py` — mineur, non bloquant.

## Décision

La review est écrite dans `runs/T022/reviews/review-attempt-1.md`.

IMPLEMENTATION_APPROVED
