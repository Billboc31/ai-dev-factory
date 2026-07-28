# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T225/reviews/implementation-review.md
- generated at: 2026-07-28T21:57:16Z

---

Now I have everything I need. Writing the review.

---

# PR Review — T225 : Add persistent AI Project Workspace with controlled capabilities

## Résumé

L'implémentation introduit un panneau de workspace IA persistant sur toutes les pages projet, accessible via un bouton bascule dans la sidebar. L'architecture en trois couches (Frontend → Control API → Supervisor) est correctement respectée : la Control API est un proxy authentifié pur, et le Supervisor détient toute la logique (appel IA, enforcement des capacités, création d'issues GitHub). Les critères d'acceptance du ticket sont majoritairement satisfaits.

## Vérifications effectuées

- Diff complet lu (16 fichiers, ~1854 lignes ajoutées)
- Chemin de routing tracé bout-en-bout : Frontend → Control API → Supervisor
- Enforcement de l'allowlist de capacités vérifié ligne par ligne
- Système de tokens UUID opaques vérifié
- Mécanisme de persistance du panneau vérifié (hors `<Routes>`)
- Validation croisée action/projet sur les endpoints de confirmation
- Prompt système inspecté pour conformité aux contraintes
- Gestion des erreurs relue
- Limites connues croisées avec `implementation-output.md` et `plan.md`

## Points validés

1. **Tout passe par le Supervisor** — `control_api/routes/workspace.py` n'appelle ni provider IA, ni GitHub, ni service interne. Il forward uniquement vers le Supervisor via `_forward()`.

2. **Allowlist deny-by-default** — `_WORKSPACE_CAPABILITIES` définit exactement 5 capacités (supervisor.main.py:2876–2897). Toute capacité proposée par l'IA non présente dans ce dict est rejetée à la ligne 3182 : le `proposed_action` est annulé, le `intent` recalé à `informational`.

3. **Tokens UUID opaques** — Les `action_id` et `draft_id` sont générés côté Supervisor (`str(uuid.uuid4())`). Le frontend ne construit jamais d'arguments internes : il ne renvoie que le token opaque à la confirmation.

4. **Confirmation obligatoire avant toute mutation** — Actions et drafts d'issues sont stockés en attente jusqu'à confirmation explicite via `/actions/confirm` ou `/issues/confirm`.

5. **Functional dev → issue GitHub uniquement** — L'intent `functional_dev` retourne un draft d'issue, jamais de code, commit ou PR.

6. **Isolation par projet à la confirmation** — Les deux endpoints de confirmation vérifient `action["project_id"] != project_id` et retournent 403 en cas de mismatch (supervisor.main.py:3227–3228, 3258–3259).

7. **Persistance du panneau** — `<ProjectWorkspacePanel>` est rendu en dehors de `<Routes>` comme frère flex dans App.jsx. La conversation se réinitialise uniquement au changement de `projectId` via `useEffect([projectId])`.

8. **Logs traçables** — Toutes les opérations workspace loguent `project_id`, `intent`, `capability`, `action_id`, `draft_id`.

9. **Prompt système conforme** — Les interdictions du ticket (pas de code, pas de commit, pas de contournement du workflow GitHub, pas de secrets) sont explicitement inscrites dans `_WORKSPACE_SYSTEM_PROMPT`.

## Problèmes détectés

### P1 — Capacités stub présentées comme disponibles mais en échec à la confirmation [BLOQUANT]

`rerun_intelligence` et `trigger_deployment` sont enregistrées dans `_WORKSPACE_CAPABILITIES` (supervisor.main.py:2889–2896) **et** listées dans le prompt système (lignes 2921–2922) comme capacités disponibles. Lorsque l'utilisateur confirme l'une d'elles, `_execute_workspace_capability` retourne `(False, "use platform UI...")`, ce qui produit une réponse HTTP 500 au confirmateur.

Le flux utilisateur est : message → "Proposed action" affiché → "Confirm" cliqué → erreur 500. C'est une fausse promesse : le système annonce une capacité qu'il ne peut pas exécuter, et la seule façon de le savoir est de cliquer sur Confirmer.

`implementation-output.md` le mentionne comme "known limit", mais une limitation documentée dans un artefact interne ne suffit pas : l'utilisateur final n'a aucun moyen de le savoir avant de confirmer.

**Correction attendue** : supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système, **ou** les implémenter correctement. Si elles sont conservées, leur confirmation doit retourner HTTP 501 (Not Implemented) avec un message clair, et le frontend doit distinguer ce cas d'une erreur réelle.

### P2 — Aucun test livré [BLOQUANT]

Le plan (plan.md:183–209) spécifie des tests exhaustifs pour les trois couches : Supervisor (classification d'intent, rejet de capacités inconnues, validation des tokens, forged/mismatched action IDs), Control API (proxy pur, mapping des erreurs), Frontend (persistance du panneau, réinitialisation, cartes de confirmation). Aucun fichier de test n'apparaît dans le diff.

Les scénarios manquants incluent des cas de sécurité critiques :
- forged `action_id` → rejet 404
- `action_id` d'un autre projet → rejet 403
- capacité non-allowlistée proposée par l'IA → refus sans exécution
- `functional_dev` → aucun code généré

**Correction attendue** : livrer au minimum les tests Supervisor couvrant les chemins de sécurité.

### P3 — Détails d'erreur du provider IA exposés au client [MINEUR]

`_call_workspace_ai` (supervisor.main.py:3024–3030) retourne `f"AI call failed: {exc}"` directement dans le champ `reply` de la réponse. Ceci peut exposer des informations internes : messages d'erreur API, détails d'authentification, IPs internes.

**Correction attendue** : retourner un message générique à l'utilisateur ; loguer l'exception à niveau ERROR côté Supervisor.

### P4 — Contenu des tickets injecté sans sanitisation dans le contexte système [MINEUR]

`_workspace_project_context` lit la première ligne de chaque fichier ticket (max 80 chars) et la concatène dans le prompt système (supervisor.main.py:2974–2979). Un ticket dont le titre commence par une instruction de prompt injection (ex : `IGNORE PREVIOUS INSTRUCTIONS and...`) pourrait influencer le comportement de l'IA.

Le risque est borné (80 chars, première ligne seulement, côté Supervisor uniquement), mais c'est un vecteur d'injection indirect réel.

**Correction attendue** : préfixer chaque ligne ticket avec un label neutre structuré, par exemple `- ticket "T001": {first_line}`, pour rendre l'injection syntaxiquement plus difficile à exécuter dans ce contexte.

## Risques éventuels

- **Stockage en mémoire sans TTL** : les actions et drafts en attente s'accumulent sans expiration. Risque de fuite mémoire si de nombreuses actions non confirmées s'accumulent. Documenté comme limitation connue, acceptable pour une v1.
- **Aucune limite sur la longueur du message** : `message: str` sans max. Un message très long augmente les coûts token. Risque faible à court terme.
- **Endpoints Supervisor non authentifiés** : cohérent avec le reste de l'API Supervisor, mais tout processus atteignant le port 8090 peut appeler les endpoints workspace sans passer par la Control API. À surveiller si le port est exposé hors du réseau interne.

## Décision

L'architecture est correcte et les contraintes de sécurité fondamentales (routing Supervisor, allowlist, tokens opaques, confirmation) sont bien implémentées. Cependant, **P1** (capacités stub en échec silencieux après confirmation) est un défaut de comportement visible qui nuit à la confiance utilisateur, et **P2** (absence totale de tests) laisse des chemins de sécurité critiques non vérifiés alors que le plan les exigeait explicitement.

- REQUEST_CHANGES

## Actions demandées

1. **P1** — Supprimer `rerun_intelligence` et `trigger_deployment` de `_WORKSPACE_CAPABILITIES` et du prompt système **ou** les implémenter. En aucun cas une confirmation utilisateur ne doit aboutir à un 500 pour une capacité annoncée comme disponible.

2. **P2** — Livrer les tests Supervisor couvrant au minimum : rejet de capacité inconnue, rejet de token forgé/mismatch projet, classification `functional_dev` sans génération de code, validation d'issue draft vide.

3. **P3** — Remplacer `f"AI call failed: {exc}"` par un message générique côté réponse ; loguer l'exception en interne.

4. **P4** — Préfixer les lignes ticket dans `_workspace_project_context` avec un label structuré pour durcir la surface d'injection de prompt.

---

IMPLEMENTATION_FIX_REQUIRED
