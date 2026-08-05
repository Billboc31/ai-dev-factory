# PR Review — T228: Add autonomous "Unblock this ticket" recovery action

## Résumé

L'implémentation couvre l'ensemble du périmètre fonctionnel du ticket : module `recovery.py` (classification, plan, exécution, déduplication), intégration dans `supervisor/main.py`, UI React avec confirmation et rapport, et 36 tests unitaires. Le modèle de sécurité (allowlist fermée, schémas de params validés, propositions immuables, fingerprint SHA256) est solide et bien pensé. Deux problèmes bloquants ont été identifiés, dont un deadlock de session qui rend la fonctionnalité inutilisable pour la classe de blocker `MISSING_APPROVAL`.

---

## Vérifications effectuées

- Lecture complète de `services/supervisor/recovery.py` (871 lignes)
- Lecture des sections recovery de `services/supervisor/main.py` (lignes 2895–3347 + 3530–3648 + 3711–3729)
- Lecture complète de `tests/test_workspace_recovery.py` (713 lignes, 36 tests)
- Lecture de `apps/dashboard/src/components/ProjectWorkspacePanel.jsx` (extraits recovery)
- Lecture du plan (`runs/T228/plan.md`)
- Vérification de la gestion de la concurrence, du nettoyage des sessions et du flux MISSING_APPROVAL
- Vérification du flux de création d'issue pour PRODUCT_BUG
- Vérification de la logique `verify_ticket_progress` et de ses appels

---

## Points validés

**Architecture et sécurité**

- Allowlist fermée de 7 opérations ; noms d'ops validés à la construction du plan ET à l'exécution (double-check défense en profondeur).
- `param_schema` par opération : seules les valeurs énumérées acceptées ; chemins filesystem libres, noms de services arbitraires, commandes shell impossibles à injecter.
- Propositions immuables : le frontend envoie uniquement `{ action_id }` à la confirmation ; les opérations exécutées proviennent exclusivement de `_proposals[proposal_id].operations`.
- Fingerprint SHA256 (`StateFingerprint.version`) : si l'état du ticket change entre prepare et execute, le 409 `PROPOSAL_STALE` est retourné et aucune opération n'est appliquée.
- Session unique par ticket : verrou `_session_lock` + check atomique → une seule session active ; deuxième appel concurrent reçoit `RECOVERY_IN_PROGRESS`.
- Verrou libéré même sur exception (`try/finally` dans `_prepare_recovery`).
- `MISSING_APPROVAL` : plan vide → zéro opérations mutantes (testé).
- Corps des issues GitHub sanitisé : pas de secrets, chemins privés, ou logs non filtrés.
- `gh` CLI invoqué avec des arguments statiques construits server-side ; aucune donnée frontend ne compose les commandes shell.

**Fonctionnalités**

- Les 11 valeurs de `BlockerClass` sont couvertes par `classify_blocker` (pure function, sans LLM).
- Les 10 `RecoveryStage` sont exposés dans l'UI avec codes couleur corrects.
- Déduplication d'issue : signature déterministe (5 champs structurels), recherche avant création.
- Bouton "Unblock ticket" suggéré apparaît sur `NEEDS_USER_INPUT` et `FAILED`.
- Carte de confirmation affiche `ticket_id`, `blocker_class`, et tableau des opérations avec niveau de risque.
- Carte de rapport collapsible avec résultat par opération (✓/✗), lien issue bug cliquable.
- Endpoint de polling `GET /api/recovery/{session_id}` : 404 tant qu'en cours, 200 à l'état terminal.
- `recover_ticket` dans `_WORKSPACE_CAPABILITIES` avec `confirmation_required: True`.
- Message "Unblock this ticket" mappe vers `recover_ticket` (système prompt, test dédié).

**Tests**

- Couverture des cas de sécurité : injection d'op inconnue, chemin arbitraire en param, service_id hors enum → `ValueError`.
- Test de concurrence avec `threading.Barrier`.
- Test de non-mutation : `state.json` inchangé après `_prepare_recovery`.
- Tests paramétrés sur les 11 `BlockerClass`.

---

## Problèmes détectés

### [BLOCKING] 1 — Deadlock de session pour MISSING_APPROVAL

**Fichiers** : `services/supervisor/main.py` (l. 3090–3102), `apps/dashboard/src/components/ProjectWorkspacePanel.jsx` (l. 124–129)

**Description** :

`_prepare_recovery` crée toujours une entrée dans `_active_sessions` (sous verrou), quelle que soit la classe de blocker. Le nettoyage de `_active_sessions` n'est effectué que dans le bloc `finally` de `_execute_recovery` (l. 3331–3332).

Pour `MISSING_APPROVAL` (et `WORKING_TREE_CONFLICT`, `USER_DECISION_REQUIRED`), le plan retourné a des opérations vides. L'UI désactive le bouton "Confirm Recovery" quand `!action.operations?.length` (l. 124–125 du JSX). Donc `_execute_recovery` n'est jamais appelé depuis l'UI, et `_active_sessions[ticket_id]` n'est jamais nettoyé.

**Impact** :

Après un diagnostic `MISSING_APPROVAL`, toute nouvelle tentative "Unblock this ticket" sur le même ticket retourne `RECOVERY_IN_PROGRESS` de façon permanente, sans possibilité de déblocage sans redémarrage du superviseur. Ce cas est très courant (ticket en attente de review), ce qui rend la fonctionnalité inutilisable dans ce scénario.

**Correction attendue** : Option A — dans `_prepare_recovery`, lorsque le plan est vide (aucune opération), retirer le ticket de `_active_sessions` avant de retourner. Option B — activer le bouton Confirm même pour les plans vides et laisser `_execute_recovery` retourner `NEEDS_USER_INPUT` immédiatement (flow already tested and working).

---

### [BLOCKING] 2 — Issue bug non créée si les opérations échouent pour PRODUCT_BUG

**Fichier** : `services/supervisor/main.py` (l. 3251–3287)

**Description** :

La création de l'issue GitHub n'est déclenchée que dans la branche `if advanced:` (l. 3251–3254), c'est-à-dire uniquement si le ticket est considéré comme "RECOVERED". Si une opération du plan `PRODUCT_BUG` échoue et que la session atteint `FAILED`, aucune issue n'est créée.

L'exigence du ticket est explicite :

> When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue.

L'identification du bug se fait à la classification (`classify_blocker`), pas uniquement à la récupération réussie. Un bug reproductible qui empêche la récupération est précisément le cas le plus critique.

**Correction attendue** : déplacer la création d'issue bug en dehors de `if advanced:` — elle doit s'exécuter dès que `proposal.blocker_class == BlockerClass.PRODUCT_BUG`, indépendamment du succès des opérations, dans le bloc `finally` ou juste avant.

---

### [OBSERVATION] 3 — Sémantique trompeuse de `verify_ticket_progress`

**Fichier** : `services/supervisor/main.py` (l. 3248) + `services/supervisor/recovery.py` (l. 854–870)

**Description** :

`_execute_recovery` passe `proposal.state_fingerprint.ticket_state` (l'état au moment de prepare) comme `expected_next_state`. La fonction retourne `(True, state)` si l'état courant == `expected_next_state`. Donc si l'état n'a pas changé (cas normal pour `retry_stage` qui n'écrit qu'un marker), `advanced = True` et la session est marquée `RECOVERED`.

L'implémentation est cohérente avec les tests (le test accepte explicitement `advanced is True` quand l'état est inchangé), mais la sémantique est trompeuse pour les utilisateurs — un ticket dont le daemon n'a pas encore lu le marker peut être affiché comme "RECOVERED".

Ce n'est pas un bug bloquant compte tenu du caractère asynchrone du daemon, mais le nommage `expected_next_state` et `advanced` devrait être revu pour éviter la confusion (ex. `expected_baseline_state`, `not_regressed`).

---

### [OBSERVATION] 4 — `_results` et `_proposals` : fuite mémoire (TTL non implémenté)

**Fichier** : `services/supervisor/main.py` (l. 2897–2900)

**Description** :

Le plan mentionne explicitement "TTL of 30 minutes enforced by a cleanup task" pour `_results`. Ni le TTL ni la tâche de nettoyage ne sont implémentés. `_proposals` n'est jamais purgé non plus. Ces dicts croissent sans borne en production.

---

### [OBSERVATION] 5 — `regenerate_artifact` pour STATE réinitialise toujours à "PLAN"

**Fichier** : `services/supervisor/recovery.py` (l. 240–244)

**Description** :

```python
target.write_text(
    json.dumps({"ticket_id": ticket_id, "state": "PLAN", "recovered": True}),
    ...
)
```

Si `state.json` est absent pour un ticket en `IMPLEMENTATION`, la régénération le remet à `PLAN`, effaçant toute progression. La présence du champ `"recovered": True` signale l'intervention mais l'opérateur doit le remarquer. Risque limité car uniquement déclenché sur un `state.json` vraiment absent.

---

### [OBSERVATION] 6 — `create_bug_issue` op : placeholder architectural

**Fichier** : `services/supervisor/recovery.py` (l. 382–387)

**Description** :

L'implémentation de l'op `create_bug_issue` est un no-op qui retourne toujours succès (`"bug issue creation delegated to recovery executor"`). La vraie création d'issue est gérée dans `_execute_recovery`, hors du dispatch d'opérations. Cette asymétrie crée une incohérence architecturale : l'op est présente dans `ALLOWLISTED_RECOVERY_OPS` et dans le plan affiché à l'utilisateur mais n'exécute rien. Cela rend le rapport d'opérations (`ops_performed`) partiellement mensonger.

---

## Risques éventuels

- **Session zombie permanente** pour `MISSING_APPROVAL` (bloquant, décrit ci-dessus).
- **Issue bug manquante** pour `PRODUCT_BUG` + échec des ops (bloquant, décrit ci-dessus).
- La commande `git fetch` via `subprocess.run` dans `_op_fetch_branch` est correctement bornée au branch lu depuis `state.json`, mais n'a pas de timeout paramétrable (hardcodé 60s). Acceptable mais à documenter.
- `classify_blocker` utilise des correspondances textuelles larges (`"rejected"`, `"internal error"`, `"conflict"`) qui peuvent produire des faux positifs. Non bloquant car la classification entraîne des opérations sûres (diagnostics + retry).

---

## Décision

- REQUEST_CHANGES

Les deux problèmes bloquants (session deadlock MISSING_APPROVAL, issue bug manquante sur récupération échouée) doivent être corrigés avant approbation. La qualité générale de l'implémentation est élevée — les corrections sont localisées et ne nécessitent pas de restructuration.

## Actions demandées

1. **[BLOCKING]** Dans `_prepare_recovery` : si `len(ops) == 0` (plan vide), retirer `ticket_id` de `_active_sessions` avant de retourner, pour éviter le deadlock session. Alternativement, activer le bouton Confirm pour les plans vides et laisser `_execute_recovery` gérer le cas `NEEDS_USER_INPUT` (flow déjà testé).

2. **[BLOCKING]** Dans `_execute_recovery` : déplacer la création d'issue bug (`search_existing_bug_issues` + `create_bug_issue`) en dehors de `if advanced:`, pour qu'elle s'exécute dès que `proposal.blocker_class == BlockerClass.PRODUCT_BUG`, indépendamment du succès des opérations.

3. **[RECOMMENDED]** Implémenter la tâche de nettoyage TTL pour `_results` (et idéalement `_proposals`) comme documenté dans le plan.

4. **[RECOMMENDED]** Ajouter un test couvrant le cas "MISSING_APPROVAL prepare → nouvelle tentative immédiate → doit réussir" pour prévenir toute régression sur le fix du point 1.

IMPLEMENTATION_FIX_REQUIRED
