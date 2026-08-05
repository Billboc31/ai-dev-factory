La review est terminée. Voici le résumé :

---

## Review T228 — Décision : `IMPLEMENTATION_FIX_REQUIRED`

L'implémentation est globalement de bonne qualité : modèle de sécurité solide (allowlist fermée, propositions immuables, fingerprint SHA256, concurrence atomique), couverture fonctionnelle complète (11 blockers, 10 stages, 7 ops, UI complète), 36 tests bien ciblés.

**Deux problèmes bloquants ont été identifiés :**

**1. Deadlock de session pour `MISSING_APPROVAL`** (`main.py` l. 3090–3102 + JSX l. 124–125)  
Quand le blocker est `MISSING_APPROVAL`, le plan est vide et le bouton Confirm est désactivé par l'UI (`disabled={!action.operations?.length}`). `_execute_recovery` n'est donc jamais appelé, et `_active_sessions[ticket_id]` n'est jamais nettoyé. Toute tentative ultérieure d'"Unblock this ticket" reçoit `RECOVERY_IN_PROGRESS` en permanence — le superviseur doit être redémarré pour débloquer.

**Correction** : dans `_prepare_recovery`, vider `_active_sessions[ticket_id]` avant de retourner si le plan est vide. Ou activer le bouton Confirm pour les plans vides (le flow `NEEDS_USER_INPUT` est déjà testé et fonctionne).

**2. Issue bug non créée sur récupération échouée pour `PRODUCT_BUG`** (`main.py` l. 3251–3254)  
La création d'issue GitHub est conditionnée à `if advanced:`. Si les opérations échouent et que la session atteint `FAILED`, aucune issue n'est créée — ce qui va à l'encontre de l'exigence : "When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue."

**Correction** : déplacer la création d'issue bug en dehors de `if advanced:`, conditionnée uniquement sur `proposal.blocker_class == BlockerClass.PRODUCT_BUG`.
