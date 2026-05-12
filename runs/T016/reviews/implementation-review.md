Now I have everything needed for the review. Let me produce the structured review.

---

# Review — T016 Runtime Prompt Snapshots

## Contexte

T016 demande la persistance automatique des runtime prompts dans `runs/TXXX/prompts/` avec naming déterministe, incrémentation des tentatives, inclusion des extra contexts, snapshot avant exécution, et logs runtime. Le plan prévoyait 2 fonctions + 1 appel + 1 fichier de tests. `run_ticket.py` ne devait pas être modifié.

## Vérification point par point

### 1. Snapshots écrits dans `runs/TXXX/prompts/`

✅ `_write_prompt_snapshot` écrit dans `Path("runs") / ticket_id / "prompts"` (`run_step.py:238`). Le dossier `runs/T016/prompts/review-attempt-1.md` existe et contient le prompt runtime complet — preuve en production que la mécanique fonctionne.

### 2. Naming déterministe

✅ Format `{step}-attempt-{n}.md` (`run_step.py:241`), conforme au ticket. Pas d'horodatage, pas d'UUID — entièrement prédictible.

### 3. Incrémentation correcte des tentatives

✅ `_next_attempt_number` (`run_step.py:230-233`) compte les fichiers glob existants et retourne `len + 1`. Testé par `test_snapshot_attempt_increment` (3 appels → `review-attempt-3.md`, `_next_attempt_number` → 4).

### 4. Extra contexts inclus

✅ Le snapshot est appelé ligne 376 **après** l'append de l'extra context (lignes 363-369). `effective_prompt` à ce point contient déjà le bloc `## Contexte de retry injecté par run_ticket.py`. Vérifié par `test_snapshot_contains_extra_context`.

### 5. Contenu identique au prompt runtime

✅ `_write_prompt_snapshot(ticket_id, step, effective_prompt)` passe la string exacte — pas de transformation, pas de résumé. Testé par `test_snapshot_content_exact`.

### 6. Snapshot avant exécution

✅ Ligne 376 (`_write_prompt_snapshot`) précède ligne 377 (`execute_external_command`). Conforme au plan et au ticket.

### 7. Runtime logs

✅ `_log_runtime(ticket_id, f"snapshot: runtime-prompt={snapshot_path}")` (`run_step.py:242`). Format exact conforme à l'exemple du ticket.

### 8. Aucune régression workflow

✅ `run_ticket.py` est inchangé. Dans `run_step.py`, seules 2 fonctions sont ajoutées et 1 appel inséré dans le bloc `if args.exec_cmd:` déjà existant. Aucune logique existante n'est modifiée. Les 31 tests passent.

### 9. Scope borné

✅ Exactement ce que le plan prévoyait : `_next_attempt_number`, `_write_prompt_snapshot`, appel dans `main()`, `tests/test_run_step_snapshots.py`. Rien de plus.

## Observations mineures (non bloquantes)

- Le double `mkdir` dans `_write_prompt_snapshot` (ligne 239) est redondant avec `ensure_run_tree`, mais inoffensif et défensif.
- Le compteur par glob n'est pas atomique (exécutions parallèles sur le même ticket/step). Documenté comme limite connue dans `implementation-output.md`. Hors scope, acceptable.

## Conclusion

L'implémentation est conforme au ticket, au plan, et aux conventions du projet. Le code est minimal, lisible, sans magie. Les tests couvrent tous les critères d'acceptation. Aucune régression introduite.

IMPLEMENTATION_APPROVED
