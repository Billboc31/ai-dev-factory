I now have everything I need. I've directly read all implementation files and verified each fix from the previous review cycle.

---

# PR Review — T225 : Add persistent AI Project Workspace with controlled capabilities (round 2)

## Résumé

Deuxième revue, après un premier cycle `IMPLEMENTATION_FIX_REQUIRED` sur quatre points (P1–P4). L'implémentation actuelle résout l'ensemble des demandes. L'architecture en trois couches (Frontend → Control API → Supervisor) est correctement respectée et les critères d'acceptance du ticket sont entièrement satisfaits.

## Vérifications effectuées

- Diff complet relu bout-en-bout (22 fichiers dans le diff vs main)
- Chaque point P1–P4 vérifié ligne par ligne dans le code actuel
- Routage Frontend → workspace.js → Control API → Supervisor tracé
- Logique `_execute_workspace_capability` relue pour cohérence avec allowlist
- Tests Supervisor relus cas par cas
- Prompt système vérifié vis-à-vis des contraintes du ticket

## Vérification des fixes précédents

### P1 — Capacités stub présentées disponibles mais en échec : RÉSOLU

`_WORKSPACE_CAPABILITIES` (supervisor/main.py:2876–2888) ne contient désormais plus que 3 entrées : `restart_daemon`, `rerun_dependency_analysis`, `resume_execution`. Les stubs `rerun_intelligence` et `trigger_deployment` ont été supprimés. Le prompt système (`_WORKSPACE_SYSTEM_PROMPT`, lignes 2909–2911) liste exactement les mêmes 3 capacités. `_execute_workspace_capability` (lignes 3044–3143) implémente les 3 cas ; le fallback final est `return False, f"unknown capability: {capability!r}"` mais ce chemin est inatteignable car `workspace_action_confirm` valide d'abord contre l'allowlist.

### P2 — Aucun test livré : RÉSOLU

`tests/test_supervisor_workspace.py` (236 lignes) livre 6 tests couvrant les chemins de sécurité critiques :
- Capacité inconnue proposée par l'IA → rejet sans stockage (`test_unknown_capability_rejected`)
- Token forgé → 404 (`test_forged_action_id_rejected`)
- `action_id` d'un autre projet → 403 (`test_action_id_project_mismatch_rejected`)
- `functional_dev` → draft_id créé, aucune action stockée (`test_functional_dev_creates_issue_draft_not_code`)
- Draft vide → 422 (`test_empty_issue_draft_rejected`)
- Réponse d'erreur générique sans fuite interne (`test_ai_error_returns_generic_message`)

### P3 — Détails d'erreur du provider IA exposés au client : RÉSOLU

`_call_workspace_ai` (lignes 3013–3021) retourne désormais `"The AI assistant is temporarily unavailable. Please try again in a moment."` en cas d'exception, et logue l'exception en interne avec `logger.error("workspace: AI call failed: %s", exc, exc_info=True)`. Aucune information interne n'atteint le client.

### P4 — Contenu des tickets injecté sans sanitisation : RÉSOLU

`_workspace_project_context` (lignes 2964–2969) préfixe chaque ligne ticket avec `  - ticket "{tf.stem}": {first}`, ce qui constitue un label structuré rendant syntaxiquement plus difficile une injection de prompt via un titre de ticket malformé.

## Points validés (préexistants, confirmés intacts)

1. **Routing exclusif via Supervisor** — `control_api/routes/workspace.py` est un proxy pur (`_forward`), sans appel IA, GitHub ou service interne.
2. **Deny-by-default** — Double enforcement : rejet à la proposition dans `workspace_chat` (ligne 3165) et revalidation à la confirmation dans `workspace_action_confirm` (ligne 3214).
3. **Tokens opaques** — `action_id` et `draft_id` sont des UUID v4 générés côté Supervisor, jamais construits par le frontend.
4. **Confirmation obligatoire avant mutation** — Les deux endpoints de confirmation valident project_id (403 si mismatch) avant toute exécution.
5. **Persistance du panneau** — `ProjectWorkspacePanel` est rendu hors de `<Routes>` dans App.jsx, reste monté lors de la navigation ; la conversation se réinitialise via `useEffect([projectId])` uniquement au changement de projet.
6. **Création d'issue GitHub** — Commande `gh` passée en liste argv (pas de shell, pas d'injection), avec timeout 30 s et gestion des cas `FileNotFoundError` et `TimeoutExpired`.
7. **Logs traçables** — `project_id`, `intent`, `capability`, `action_id`, `draft_id` loggés à chaque étape.

## Observations mineures (non bloquantes)

### O1 — Dead code dans `test_ai_error_returns_generic_message`

Les deux premiers blocs `with patch(...): pass` (lignes 194–205) ne font rien. Le test fonctionnel réel commence à la ligne 217 et est correct. Ce n'est pas un bloquant, mais le fichier serait plus lisible sans ce code mort.

### O2 — TOCTOU théorique à la confirmation d'action

Dans `workspace_action_confirm`, `action` est récupéré sous lock puis validé hors lock (lignes 3205–3215). Deux requêtes concurrentes avec le même `action_id` pourraient toutes deux passer la validation et exécuter la capacité deux fois (ex. double restart du daemon). En pratique la contrainte single-user de l'interface rend ce cas irréaliste ; le comportement est acceptable pour une v1 mais méritera une vraie protection atomique (retrieve + delete sous un seul lock) lors d'une exposition multi-utilisateur.

### O3 — Draft vide reste en mémoire après refus 422

Si un draft d'issue est stocké avec un titre ou body vide (peut arriver si l'IA retourne un draft incomplet), la confirmation retourne 422 correctement mais le draft reste dans `_pending_workspace_issues` indéfiniment. Edge case peu probable avec le prompt actuel ; acceptable pour v1.

### O4 — Aucune limite sur la longueur de `message`

`message: str` dans `WorkspaceChatRequest` n'a pas de `max_length`. Déjà noté dans la review précédente comme risque faible acceptable pour v1.

## Risques hérités (acceptés v1)

- Stockage des actions/drafts en mémoire sans TTL.
- Endpoints Supervisor non authentifiés (cohérent avec le reste de l'API Supervisor).

## Décision

Les 4 problèmes bloquants et mineurs de la review précédente sont correctement résolus. L'architecture respecte les contraintes du ticket, les chemins de sécurité critiques sont implémentés et couverts par des tests. Les observations O1–O4 ne justifient pas un nouveau cycle de fix.

IMPLEMENTATION_APPROVED
