# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T228/reviews/implementation-review.md
- generated at: 2026-08-05T22:00:11Z

---

---

# PR Review — T228: Autonomous "Unblock this ticket" recovery action

## Résumé

L'implémentation couvre l'ensemble du périmètre fonctionnel du ticket : moteur de récupération (`recovery.py`), intégration Supervisor (`main.py`), interface frontend (`ProjectWorkspacePanel.jsx`), proxy API et 36 tests unitaires. L'architecture est saine — allowlist fermée, proposals immuables, fingerprinting SHA256, concurrence atomique. Deux défauts bloquants sont identifiés avant validation.

---

## Vérifications effectuées

- Lecture de l'ensemble des fichiers modifiés/créés identifiés par `git diff main`
- Contrôle de la couverture des 11 classes de bloqueur du ticket
- Contrôle de la couverture des 10 étapes UX du ticket
- Analyse du cycle de vie des sessions (`_active_sessions`, `_proposals`, `_results`)
- Analyse du modèle de sécurité : allowlist, validation des paramètres, fingerprint TOCTOU, gate d'approbation
- Analyse du workflow de création de bug issue (déduplication, sanitisation)
- Lecture de la suite de tests (`tests/test_workspace_recovery.py`, 36 cas)

---

## Points validés

**Sécurité — modèle de contrôle**
- Toutes les opérations passent par l'allowlist fermée `ALLOWLISTED_RECOVERY_OPS` ; les noms d'opérations et les paramètres sont des enums, pas des chaînes libres. Aucun accès shell générique (`shell=True` absent).
- Les proposals sont immuables après création : le frontend ne peut envoyer qu'un `proposal_id` à la confirmation, pas redéfinir les opérations.
- Fingerprint SHA256 calculé avant et après la fenêtre prepare→execute. Un changement d'état retourne 409 `PROPOSAL_STALE` — protection effective contre les races TOCTOU.
- La gate `MISSING_APPROVAL` ne déclenche aucune opération mutante (plan vide) et termine en `NEEDS_USER_INPUT`. Aucune fabrication d'approbation.
- Les opérations Git sont bornées à `git fetch origin <branch>` ; pas de reset, force-push, ni résolution automatique de conflits.
- `MAX_RECOVERY_ITERATIONS = 3` — boucle infinie impossible.
- Lock `_session_lock` avec try-finally — pas de session fantôme sur exception en prepare.
- Timeouts explicites sur tous les sous-processus (fetch 60 s, GitHub API 30 s).

**Classification bloqueur**
- Les 11 classes du ticket (`BlockerClass`) sont toutes implémentées dans `classify_blocker()` via heuristiques déterministes, sans LLM ni input frontend.

**Étapes UX**
- Les 10 stages du ticket (`RecoveryStage`) sont présents et mappés à des couleurs distinctes dans `RecoveryStageIndicator`.

**Bug issue — déduplication et sanitisation**
- Signature déterministe (SHA256 de champs structurés uniquement, pas de texte libre LLM).
- Recherche d'issue existante avant création — pas de spam.
- Corps de l'issue construit à partir de champs structurés uniquement ; pas de logs bruts, pas de paths locaux, pas de secrets.
- URL de l'issue ajoutée au recovery report.

**Tests**
- 36 cas couvrant : absence de mutations en phase prepare, rejet d'opérations arbitraires, rejet de params arbitraires, rejet de sessions concurrentes, enforcement de la limite d'itérations, déduplication bug, résolution du ticket actif, vérification de progression, endpoint de polling.

---

## Problèmes détectés

### [BLOQUANT 1] Deadlock de session sur `MISSING_APPROVAL`

**Localisation** : `services/supervisor/main.py`, ligne ~3102 (`_prepare_recovery`) et ligne ~3332 (`_execute_recovery` finally).

**Comportement** : Quand `classify_blocker()` retourne `MISSING_APPROVAL`, `build_recovery_plan()` produit une liste vide. Dans le frontend, le bouton "Confirm Recovery" est désactivé (`disabled={!action.operations?.length}`), donc `_execute_recovery()` n'est jamais appelé. Or c'est l'unique chemin qui retire la session de `_active_sessions`. La session reste en `PLAN_READY` indéfiniment.

**Impact** : Toute tentative ultérieure d'"Unblock this ticket" sur le même ticket retourne immédiatement `RECOVERY_IN_PROGRESS`. L'utilisateur est bloqué jusqu'au redémarrage du Supervisor.

**Correction attendue** (l'une ou l'autre) :
- Option A — Dans `_prepare_recovery()`, après `build_recovery_plan()`, si le plan est vide : nettoyer `_active_sessions[ticket_id]` et retourner directement la réponse `NEEDS_USER_INPUT` sans stocker de session active.
- Option B — Activer le bouton Confirm pour les plans vides et laisser `_execute_recovery()` atteindre son bloc `NEEDS_USER_INPUT` (ligne ~3295), qui nettoie déjà la session.

Un test couvrant ce chemin exact est requis.

---

### [BLOQUANT 2] Bug issue non créée quand la récupération échoue sur `PRODUCT_BUG`

**Localisation** : `services/supervisor/main.py`, ligne ~3251 — condition `if advanced:` encapsulant la logique de création d'issue (lignes ~3254–3287).

**Comportement** : Si les opérations de recovery échouent et que `verify_ticket_progress()` retourne `False`, `advanced` est `False`, le bloc de création d'issue n'est pas exécuté, et la session termine en `FAILED` ou `NEEDS_USER_INPUT` sans aucune issue GitHub créée.

**Impact** : Violation directe du ticket — *"When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue"* — l'évidence est perdue précisément dans le cas où le bug est le plus difficile à reproduire manuellement.

**Correction attendue** : Déplacer la logique de création/liaison d'issue hors du bloc `if advanced:`, conditionner uniquement sur `proposal.blocker_class == BlockerClass.PRODUCT_BUG`. La progression du ticket et la création de l'issue sont des sorties orthogonales.

Un test vérifiant la création d'issue quand `advanced=False` et `blocker_class=PRODUCT_BUG` est requis.

---

## Risques éventuels

**MEDIUM — Pas de test de régression sur les capacités Workspace existantes**
La réponse du Supervisor charge les capabilities via `_WORKSPACE_CAPABILITIES`. L'ajout de `recover_ticket` n'est pas testé en interaction avec les autres capabilities (`restart_daemon`, `resume_execution`, etc.). Un test vérifiant l'absence de régression sur le routage des actions existantes est recommandé.

**MEDIUM — Pas de test E2E du chemin MISSING_APPROVAL dans l'UI**
Même après correction du deadlock, le parcours utilisateur complet (message → DIAGNOSING → PLAN_READY → message explicatif sans bouton Confirm → retour possible à "Unblock") n'est couvert par aucun test d'intégration.

**LOW — Incohérence UX sur le bouton Confirm désactivé**
Après correction de l'option A, l'utilisateur verra une confirmation card avec un bouton désactivé et aucun message explicatif visible sur la raison (`MISSING_APPROVAL`). Il faudrait afficher le message d'explication directement dans la card plutôt que de laisser le bouton grisé sans contexte.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **[obligatoire]** Corriger le deadlock session `MISSING_APPROVAL` dans `_prepare_recovery()` (option A ou B décrite ci-dessus) et ajouter un test vérifiant que `_active_sessions` ne retient pas de session après un plan vide.

2. **[obligatoire]** Déplacer la création de bug issue hors du bloc `if advanced:`, la conditionner sur `blocker_class == PRODUCT_BUG` uniquement, et ajouter un test vérifiant la création quand `advanced=False`.

3. **[recommandé]** Ajouter un test de non-régression sur les capabilities Workspace existantes après enregistrement de `recover_ticket`.

4. **[recommandé]** Afficher le message MISSING_APPROVAL directement dans la `RecoveryConfirmCard` (classe de bloqueur + explication de ce que l'utilisateur doit faire), pas uniquement via le bouton grisé.

IMPLEMENTATION_FIX_REQUIRED
