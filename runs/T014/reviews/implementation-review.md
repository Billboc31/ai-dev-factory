I have all the information I need. Let me now write the review.

---

# PR Review — T014 : Stabiliser le validator planner flexible

## Résumé

Ticket : T014 — stabiliser la validation planner flexible dans `run_step.py`.

Le plan identifie correctement les gaps résiduels. Cependant, l'implémentation **n'a pas été appliquée** : `implementation-output.md` contient un diff proposé, bloqué par une erreur de permissions. Le code réel dans `run_step.py` est inchangé par rapport à l'état pré-T014. Aucun test n'existe dans `tests/`.

---

## Vérifications effectuées

### Code actuel (`run_step.py`)

**`_REQUIRED_SECTION_GROUPS` (lignes 76–96) — état réel :**

| Groupe | Manquant | Statut |
|---|---|---|
| `contexte` | `"## contexte technique"` | ❌ absent |
| `objectif` | — | ✅ |
| `inclus` | doublon `"## étapes d'implémentation"` | ⚠️ doublon présent |
| `hors scope` | — | ✅ |
| `critères d'acceptation` | `"## acceptance criteria"` | ❌ absent |

Un plan avec `## contexte technique` ou `## acceptance criteria` est **encore rejeté** aujourd'hui.

**`validate_planner_output()` (lignes 265–284) :**

La détection des phrases interdites utilise `if phrase in lower` — sans aucun filtrage des blocs de code ou des exemples entre backticks. La fausse positive décrite dans le ticket (mention explicative d'un garde-fou comme objet de test) **n'est pas corrigée**.

**Tests — `tests/` :** vide. Aucun fichier de test n'existe.

### Plan (`runs/T014/plan.md`)

Le plan est structurellement valide et identifie 3 des 4 gaps réels :

- ✅ Ajouter `"## contexte technique"` au groupe `contexte`
- ✅ Ajouter `"## acceptance criteria"` au groupe `critères d'acceptation`
- ✅ Retirer le doublon dans `inclus`
- ✅ Créer 5 tests unitaires

**Gap du plan :**

Le ticket exige explicitement (Section 3 et Section 4, 6e test) :
> "Le validator ne doit pas rejeter un plan uniquement parce qu'il décrit ces garde-fous comme règles à tester."

Le plan **n'inclut pas** de correction pour la fausse positive sur phrases interdites, et ne prévoit que 5 tests alors que le ticket en liste 6. Le 6e test manquant est : _"un plan valide mentionnant les garde-fous interdits comme objets de test"_ — ce test nécessite une correction de code pour être vert.

Note : l'`implementation-output.md` montre que le coder avait identifié ce gap et proposé une correction (`re.sub` pour strip les blocs de code), mais cette correction n'était pas planifiée et n'a pas été appliquée.

### Compatibilité workflow

- `run_ticket.py` importe `validate_planner_output` correctement (ligne 28) ✅
- `auto_run()` appelle `validate_planner_output(output_content)` après l'étape planner (lignes 551–558) ✅
- `_log_runtime` utilisé dans les deux modules ✅
- Changements de scope : bornés au ticket ✅

---

## Points validés

- Architecture générale du validator : correcte
- Import `subprocess` présent (pas d'artefact `subprocessf`) ✅
- `_REQUIRED_SECTION_GROUPS` utilisé, validation par groupes ✅
- Garde-fous `_FORBIDDEN_PHRASES` et `_MIN_WORD_COUNT` présents ✅
- Compatibilité `--auto` : aucun impact négatif ✅
- Logs runtime : conservés ✅
- Scope : aucun refactor transversal ✅

---

## Problèmes détectés

### P1 — Implémentation non appliquée (bloquant)

`implementation-output.md` est un diff proposé, non exécuté. Le code réel dans `run_step.py` n'a pas changé. Les bugs identifiés dans le plan existent encore en production.

### P2 — Fausse positive phrases interdites non couverte (bloquant)

Le plan ne prévoit pas de corriger `if phrase in lower` pour éviter les faux positifs quand une phrase interdite apparaît dans un exemple ou un bloc de code d'un plan. C'est une exigence explicite du ticket. Sans cette correction, un plan citant ses propres garde-fous dans un contexte de test sera rejeté.

### P3 — 6e test manquant au plan (bloquant)

Le ticket liste 6 tests ; le plan n'en prévoit que 5. Le test manquant ("un plan valide mentionnant les garde-fous interdits comme objets de test") valide précisément la correction P2.

### P4 — Mismatch reviewer/state machine (mineur, à surveiller)

L'état courant du state machine est `IMPLEMENTATION_REVIEW_NEEDED` (commit `dbacb87`). Le reviewer prompt produit des keywords `PLAN_APPROVED` / `PLAN_FIX_REQUIRED`. Ces keywords ne seront pas reconnus par `_determine_next_state()` qui attend `IMPLEMENTATION_APPROVED` ou `IMPLEMENTATION_FIX_REQUIRED`. À corriger dans le prompt reviewer ou dans l'état machine avant de relancer `--auto`.

---

## Risques éventuels

- Si l'état est transitionné manuellement à `PLAN_FIX_REQUIRED` sans que le plan soit corrigé, le planner risque d'être relancé sans corriger P2 et P3.
- La fausse positive sur phrases interdites peut bloquer des plans légitimes en production.

---

## Décision

**PLAN_FIX_REQUIRED**

---

## Actions demandées

1. **Corriger le plan (`runs/T014/plan.md`)** pour inclure :
   - Étape explicite : filtrer les blocs de code/backticks avant la recherche de phrases interdites dans `validate_planner_output()`
   - 6e test unitaire : plan valide mentionnant une phrase interdite dans un exemple de code ou d'explication

2. **Appliquer l'implémentation** : les permissions doivent être accordées pour que run_step.py soit modifié et que `tests/test_validate_planner_output.py` soit créé.

3. **Corriger le prompt reviewer** (ou l'état) : aligner les keywords de sortie (`PLAN_APPROVED`/`PLAN_FIX_REQUIRED` vs `IMPLEMENTATION_APPROVED`/`IMPLEMENTATION_FIX_REQUIRED`) avec l'état machine courant avant de relancer `--auto`.
