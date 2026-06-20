# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T197/reviews/implementation-review.md
- generated at: 2026-06-20T06:53:26Z

---

Now I have everything needed to write the structured review.

---

# PR Review — T197: Add advisory ticket intelligence analysis before development cycle

## Résumé

Implémentation fonctionnellement solide et bien architecturée. Tous les critères fonctionnels du ticket sont couverts : architecture hybride (extracteur déterministe + analyseur IA), endpoints API avec idempotence, schéma DB avec les 26 champs requis, panneau UI affichant toutes les informations demandées avec le badge "Advisory only", et non-interférence avec le scheduler. Cependant, deux critères d'acceptation concernant la couverture de tests sont explicitement manquants : `_normalize()` n'a aucun test direct, et `TicketIntelligencePanel` n'a aucun test de rendu.

---

## Vérifications effectuées

- Schéma DB (SQLite + Postgres) vs champs requis par le ticket
- Extracteur déterministe : tous les signaux requis par le ticket
- Flux de l'analyseur : subprocess, extraction JSON, normalisation, persistance
- Endpoints API : GET/POST, idempotence, gestion d'erreurs, codes HTTP
- Composant UI : champs affichés, badge advisory, polling, états
- Suite de tests : 41 tests (21 extracteur + 7 DB + 13 API)
- Template de prompt et rôle IA
- Non-interférence avec le scheduler

---

## Points validés

1. **Schéma DB complet** — les 26 champs requis sont présents dans les deux backends (SQLite `runtime_db.py:67-96`, Postgres `runtime_db_pg.py:99-130`), avec upsert correct et préservation du `created_at`
2. **Extracteur déterministe complet** — `ticket_intelligence_extractor.py` couvre les 11 signaux requis par le ticket : `text_length`, `requirement_count`, `acceptance_criteria_count`, `risky_keywords_found`, `affected_domains`, `dependency_hint_count`, `referenced_ticket_ids`, `estimated_token_size`, `rough_file_impact`, `changes_scheduler`, `likely_needs_db_migration`
3. **Architecture hybride respectée** — flux Python-extractor → AI subprocess → JSON normalization → DB conforme au schéma du ticket
4. **Normalisation robuste** — `_normalize()` (analyzer.py:90-160) clampe les scores, valide `autonomous_execution_recommendation` contre un frozenset, calcule le coût via `model_catalog` si absent
5. **Idempotence API** — guard sur statuts `queued`/`running` empêche les doubles threads (intelligence.py:156-158)
6. **202 immédiat + daemon thread** — design correct pour ne pas bloquer le client
7. **Toutes les pannes persistées** — `run_analysis` ne propage jamais d'exception, les erreurs (timeout, rc!=0, JSON invalide) vont en DB avec `status=failed`
8. **UI couvre tous les champs requis** — difficulty, risk, model, cost, queue rank, autonomous_execution, human plan/code review, dependency hints, complexity factors, summary, last analyzed date
9. **Badge "Advisory only"** visible dans le header du composant (TicketIntelligencePanel.jsx:122)
10. **Scheduler non affecté** — aucun point d'intégration avec la file, le routing, ou les dépendances
11. **`computed_signals_json` persisté et retourné** via API pour le debugging
12. **Postgres multi-tenant** — `project_id` dans le schéma et clé composite `(project_id, ticket_id)`
13. **Extracteur : 21 tests** couvrent cas simples, complexes, entrées vides, toutes les combinaisons de signaux — tous passent
14. **DB : 7 tests** couvrent upsert, timestamps, isolation multi-tickets

---

## Problèmes détectés

### [BLOQUANT 1] — `_normalize()` non testée directement (violation AC explicite)

Le critère d'acceptation stipule : *"Tests cover database persistence, API response, **analyzer normalization**, and UI rendering."*

La fonction `_normalize()` dans `ticket_intelligence_analyzer.py:90-160` n'a **aucun test direct**. Les 13 tests API (`test_ticket_intelligence_api.py`) moquent entièrement `run_analysis` via `patch("ticket_intelligence_analyzer.run_analysis")`, ce qui signifie que `_normalize()` et `_extract_json()` ne sont **jamais exercées** dans la suite de tests.

Chemins critiques non testés :
- Clamping de scores hors-range (0 → 1, 11 → 10)
- `autonomous_execution_recommendation` invalide → fallback `"plan_review_required"`
- `cost_min/max` absents → appel `estimate_cost()`
- `complexity_factors`/`dependency_hints` non-liste → `[]`
- `_extract_json()` avec sortie entourée de texte, bloc markdown ` ```json `, JSON invalide, output vide

**Correction requise** : Ajouter `tests/test_ticket_intelligence_normalizer.py` avec des tests unitaires directs sur `_normalize()` et `_extract_json()`.

---

### [BLOQUANT 2] — Aucun test pour le composant UI (violation AC explicite)

Le critère d'acceptation stipule : *"Tests cover database persistence, API response, analyzer normalization, **and UI rendering**."*

`TicketIntelligencePanel.jsx` n'a aucun test. Aucun fichier de test associé n'a été trouvé.

**Correction requise** : Ajouter des tests React (vitest + `@testing-library/react` ou équivalent du projet) couvrant au minimum :
- Rendu de l'état `not_started` ("No analysis yet")
- Affichage des données `completed` avec les champs clés (difficulty, risk, model, cost, advisory badge)
- Présence du badge "Advisory only — not used by scheduler yet"
- Rendu de l'état `failed` avec le message d'erreur

---

### [MINEUR 1] — Échec silencieux de la lecture du ticket

`_read_ticket_content()` dans `intelligence.py:101-111` capture toutes les exceptions sans log :

```python
except Exception:
    pass
return ""
```

Si `ticket.md` ne peut pas être lu pour une raison légitime (permissions, disque plein, path mal résolu), l'analyseur IA tourne avec un contenu vide sans aucun signal. Résultat : analyse potentiellement incohérente persistée comme `completed` sans que personne soit notifié.

**Correction suggérée** : `logger.warning("could not read ticket.md for %s: %s", ticket_id, exc)` dans le bloc `except`.

---

### [MINEUR 2] — Injection de variables dans le template de prompt

Dans `ticket_intelligence_analyzer.py:237-239` :

```python
prompt = template.replace("{{ticket_content}}", ticket_content)
prompt = prompt.replace("{{computed_signals}}", computed_signals_json)
```

Si le contenu d'un ticket contient littéralement la chaîne `{{computed_signals}}`, cette chaîne sera remplacée par les signaux JSON lors du second `.replace()`, polluant la section "Ticket Content" du prompt avec des données JSON injactées. Pas de RCE, mais pollution du contexte AI et résultats imprévisibles. Probabilité faible en pratique.

**Correction suggérée** : Utiliser un séparateur qui ne peut pas apparaître dans le contenu (ex. blocs XML/CDATA), ou remplacer les deux placeholders en une seule passe avec un remplacement simultané.

---

## Risques éventuels

- Timeout `_ANALYSIS_TIMEOUT = 120` hardcodé — non configurable via env ou app state, peut être insuffisant pour des modèles lents ou des tickets volumineux
- `daemon_exec_cmd` par défaut à `"claude --dangerously-skip-permissions"` est acceptable pour ce projet mais non documenté
- `model_catalog.py` hardcodé — pas de mécanisme de mise à jour des tarifs sans modification du code

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **[Bloquant]** Ajouter `tests/test_ticket_intelligence_normalizer.py` avec tests unitaires directs pour `_normalize()` : clamping de scores, fallback autonomous_rec, fallback de coût, sérialisation JSON, valeurs None/invalides
2. **[Bloquant]** Ajouter tests unitaires pour `_extract_json()` : JSON direct valide, JSON dans bloc markdown, JSON précédé de texte libre, sortie vide/invalide
3. **[Bloquant]** Ajouter tests pour `TicketIntelligencePanel.jsx` couvrant les états `not_started`, `completed` (champs remplis), badge "Advisory only", état `failed`
4. **[Mineur]** Ajouter `logger.warning(...)` dans le `except` de `_read_ticket_content()` pour loguer les erreurs réelles
5. **[Mineur]** Documenter ou corriger le risque d'injection de template dans `run_analysis()` via les deux `.replace()` en chaîne

IMPLEMENTATION_FIX_REQUIRED
