---

# PR Review — T197 · Ticket Intelligence Analyzer

## Résumé

Implémentation d'un nouveau composant d'analyse préalable des tickets, purement advisory, couvrant extraction de signaux déterministes (Python), classification IA, persistance SQLite/PostgreSQL, API REST, interface React et suite de tests complète. Aucun changement au scheduler ou à l'exécution des tickets.

---

## Vérifications effectuées

- Lecture complète des fichiers créés/modifiés : extractor, analyzer, model_catalog, runtime_db, routes/intelligence, schemas, TicketIntelligencePanel, TicketDetailPage, tickets.js, tests
- Vérification du schéma DB (SQLite + PostgreSQL)
- Vérification du flow hybride (extractor → AI → normalize → persist → display)
- Vérification de l'isolation du scheduler (run_ticket.py non modifié)
- Vérification de la couverture de tests

---

## Points validés

**Exigences fonctionnelles**

- Tous les champs demandés par le ticket sont présents en base (`ticket_intelligence`, 28 colonnes)
- Le flow hybride est correctement implémenté : `extract_signals()` → prompt avec signaux + contenu → AI subprocess → `_normalize()` → `upsert_ticket_intelligence()`
- Les 11 signaux déterministes sont extraits sans appel réseau ni effet de bord
- Les signaux sont persistés dans `computed_signals_json` — accessibles pour debug
- L'upsert est idempotent : re-lancer l'analyse met à jour le résultat existant
- Les endpoints GET et POST sont présents avec variantes project-scoped
- La réponse POST est un 202 avec `analysis_status: queued` — non-bloquant
- Le scheduler existant n'est pas touché

**Qualité du code**

- `_extract_json()` robuste : JSON brut, code fences markdown, recherche greedy — trois couches de fallback
- `_normalize()` défensive : clamping 1–10, labels auto-dérivés, defaults sensés, enum validé pour `autonomous_execution_recommendation`
- Injection template protégée : `_TEMPLATE_VARS_RE` en substitution simple passe (pas de risque de cross-injection)
- Idempotence sur POST concurrent : vérification du statut avant spawn de thread
- Toutes les erreurs AI (timeout, rc != 0, JSON invalide, exception) sont capturées et persistées avec `analysis_status: failed` — aucune erreur silencieuse

**Interface utilisateur**

- Badge "Advisory only — not used by scheduler yet" présent
- Polling 4 s arrêté proprement à la fin de l'analyse
- États visuels distincts : not_started / queued (jaune pulse) / running (bleu pulse) / completed (vert) / failed (rouge)
- Tous les champs requis affichés : difficulty, risk, model, cost, queue, human review, dependencies, complexity factors, summary, last analyzed
- Bouton désactivé pendant analyse active

**Tests**

- Extractor : 24 tests, tous les 11 signaux couverts
- Normalizer : 50+ tests, clamping, defaults, enum, serialisation JSON, round-trip complet
- DB : 11 tests, insert/update/multi-tickets/préservation created_at
- API : 18 tests, GET/POST, 404, 503, idempotence, background completion, project-scoped
- Frontend : 20+ tests, états, bouton, polling, rendu des champs

---

## Problèmes détectés

### Mineurs (non bloquants)

**1. `project_id` ignoré dans les routes project-scoped (SQLite path)**

`routes/intelligence.py:178–189` — Les handlers `get_intelligence_project` et `analyze_intelligence_project` délèguent directement aux handlers flat en ignorant `project_id`. Pour SQLite c'est acceptable (une DB par projet), mais le contrat API implique un filtrage par `project_id` qui n'est pas appliqué. Une requête `GET /projects/X/tickets/T001/intelligence` retourne la même réponse que `GET /projects/Y/tickets/T001/intelligence`. Risque de confusion si plusieurs projets partagent le même SQLite.

**2. Stale status au redémarrage du serveur**

`routes/intelligence.py:166–173` — Le background thread est `daemon=True`. Si le processus FastAPI redémarre pendant une analyse, le statut reste `queued` ou `running` indéfiniment dans la DB. Il n'y a pas de réinitialisation des statuts actifs au démarrage. Un ticket en statut `running` ne peut plus être re-analysé via POST (l'idempotence bloque le re-spawn). L'utilisateur devrait manuellement corriger la DB.

**3. Analyse lancée sur contenu vide sans avertissement**

`routes/intelligence.py:101–111` — `_read_ticket_content()` retourne une string vide si `ticket.md` est introuvable, loggue un warning, mais l'analyse se lance quand même. L'AI produira une analyse inutile ou hors-sujet. Un 422 ou un message explicite dans `analysis_summary` serait plus clair.

**4. Coût `local-qwen` affiché comme `$0.000 – $0.000 USD`**

`model_catalog.py:42–45` — Le calcul ±20% sur base 0 donne toujours 0.0. L'UI affichera `$0.000 – $0.000 USD`. Esthétiquement, un label `free / local` serait plus lisible, mais ce n'est pas un dysfonctionnement.

---

## Risques éventuels

- Le thread daemon peut être tué silencieusement en cas de redémarrage (voir point 2 ci-dessus) — risque faible pour un feature advisory
- L'`exec_cmd` configuré par défaut (`claude --dangerously-skip-permissions`) dépend de l'environnement d'exécution ; si Claude CLI n'est pas disponible, toutes les analyses échouent avec `rc != 0` et un message clair en DB
- Pas de rate-limiting sur le POST `/analyze` : un client peut déclencher de nombreuses analyses en rafale sur différents tickets — acceptable en phase advisory mais à monitorer

---

## Décision

L'implémentation couvre l'intégralité des acceptance criteria du ticket T197. Le flow hybride est correct, propre et bien testé. Les problèmes détectés sont tous mineurs et n'affectent pas la fonctionnalité principale. Le scheduler est intact. L'UI est conforme aux exigences.

IMPLEMENTATION_APPROVED
