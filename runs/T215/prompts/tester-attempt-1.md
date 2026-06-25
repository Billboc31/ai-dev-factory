# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

The ticket follows.


# T215 — Add Global Runtime Settings page backed by database with hot-reload support (V1)

**Source**: GitHub Issue #286

## Description

# Add Global Runtime Settings page backed by database with hot-reload support (V1)

## Context

AI Dev Factory currently relies heavily on environment variables and configuration values spread across `.env` files and runtime defaults.

This makes configuration difficult because:

- settings cannot be modified from the UI
- changing values often requires editing files manually
- administrators cannot easily inspect the current runtime configuration
- configuration tuning for demos and experiments is cumbersome

As AI Dev Factory evolves toward a multi-project autonomous platform, configuration should become first-class and manageable directly from the application.

## Goal

Introduce a first version of a Global Runtime Settings page.

Configuration values must be stored in the runtime database and loaded dynamically by the application.

The objective of V1 is to allow administrators to inspect and modify important runtime settings directly from the dashboard.

## Architecture

Use the following precedence order:

```text
Runtime Settings DB
↓
.env fallback
↓
hardcoded defaults
```

The `.env` file remains the bootstrap mechanism.

The new database-backed settings layer overrides bootstrap values when present.

## Database model

Create a new table:

```text
runtime_settings
```

Suggested fields:

```text
key                TEXT PRIMARY KEY
value              TEXT NOT NULL
value_type         TEXT NOT NULL
scope              TEXT DEFAULT 'global'
description        TEXT
is_sensitive       BOOLEAN DEFAULT FALSE
requires_restart   BOOLEAN DEFAULT FALSE
updated_at         TEXT
updated_by         TEXT
```

V1 supports only:

```text
scope = global
```

Project-scoped settings are out of scope.

## Dashboard UI

Add a new administration page:

```text
Global Settings
```

The page should display:

```text
Setting name
Current value
Description
Editable status
Sensitive flag
Requires restart flag
Source (db/env/default)
```

Settings should be editable directly from the UI.

## Candidate settings for V1

Examples:

```text
DEFAULT_PLANNER_MODEL
DEFAULT_CODER_MODEL
DEFAULT_REVIEWER_MODEL
DEFAULT_TESTER_MODEL
MAX_WORKERS
INTELLIGENCE_TIMEOUT_SECONDS
DISPATCHER_ENABLED
LOG_LEVEL
```

Additional settings may be added if useful.

## Hot reload requirement

V1 should support hot reload whenever reasonably possible.

The application should re-read runtime settings dynamically instead of requiring process restarts.

Expected behavior:

```text
change MAX_WORKERS
↓
save
↓
new value immediately available
```

For settings that cannot safely be hot-reloaded:

```text
requires_restart = true
```

The UI must clearly indicate:

```text
Restart required
```

No automatic restart is required in V1.

## Sensitive values

Sensitive values must not be displayed in plain text.

Examples:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GITHUB_TOKEN
```

V1 behavior:

```text
show only configured / not configured
allow replacement
never reveal existing secret values
```

Full secret management improvements are out of scope.

## API

Introduce endpoints similar to:

```text
GET /api/settings
GET /api/settings/{key}
PUT /api/settings/{key}
```

## Non-goals

- Replacing all existing `.env` usage.
- Automatic process restart.
- Project-scoped settings.
- Secret encryption/rotation.
- Dispatcher configuration redesign.

## Acceptance criteria

- A new Global Settings page exists in the dashboard.
- Runtime settings are persisted in the database.
- Runtime settings override `.env` values when present.
- Non-sensitive settings can be edited from the UI.
- Sensitive settings are never displayed in plain text.
- The UI indicates whether a setting requires restart.
- Hot reload works for supported settings.
- Existing behavior continues to work when no DB setting exists.
- The application falls back to `.env` values when no DB override exists.
- Existing tests continue to pass and new settings tests are added.