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


# T161 — T161 - Fix Environments create flow to provision real sandbox runtime

**Source**: GitHub Issue #172

## Description

# T161 - Fix Environments create flow to provision real sandbox runtime

## Problem

Creating an Environment from the Environments tab displays an environment card in the UI, but does not create the actual sandbox runtime directory.

Example:

Requested environment:

```text
demo-ai-dev-factory
```

Observed behavior:

- environment card appears
- status/actions become available
- no real sandbox directory exists
- later actions fail with:

```text
[Errno 2] No such file or directory: '/sandboxes/demo-ai-dev-factory'
```

The environment metadata exists, but the runtime sandbox was never provisioned.

---

## Root cause hypothesis

The current Create Environment flow likely:

- creates environment metadata only
- persists an environment/sandbox identifier
- displays the environment in the UI
- but never calls the real SandboxManager provisioning/deploy flow

This creates a fake runtime state:

```text
environment exists logically
sandbox does not exist physically
```

---

# Goal

Make Create Environment provision a real runnable sandbox runtime, not only metadata.

Environment creation must go through the same runtime provisioning path used by deploy/sandbox creation flows.

---

# Included

## Real sandbox provisioning

Create Environment must:

- call SandboxManager.create(...)
- create a real sandbox directory under configured runtime root
- write `state.json`
- write `.env`
- initialize runtime directories
- create runtime metadata
- optionally start runtime services
- configure Traefik routes if applicable

---

## Persist real sandbox identifiers

Environment metadata must store the real sandbox id returned by SandboxManager.

Do not derive runtime existence from environment name alone.

---

## Prevent fake runtime states

If sandbox provisioning fails:

- environment creation must fail
- UI must display a clear error
- no fake environment card should remain visible
- no partial runtime metadata should survive

Do not show environments as:

- running
- stopped
- deployable

unless a real sandbox exists.

---

## Runtime validation after create

After environment creation:

Verify:

```text
<runtime_root>/sandboxes/<sandbox_id>/
```

exists and contains:

- `state.json`
- `.env`
- runtime directory

---

## Environment actions validation

After creation:

- Redeploy must work
- Stop must work
- Refresh must work
- Delete must work
- View Logs must work

Actions must use the real sandbox id.

---

## Suggested files to audit

- services/control_api/routes/environments.py
- services/control_api/services/environment*
- services/control_api/services/sandbox_manager.py
- services/control_api/services/deploy*
- environment create handlers
- runtime provisioning flow

---

# Tests

Add tests ensuring:

- creating an environment creates a real sandbox directory
- state.json exists after create
- .env exists after create
- failed provisioning does not leave fake environments
- runtime actions work after create
- sandbox ids come from SandboxManager

---

# Acceptance criteria

- Creating `demo-ai-dev-factory` creates a real sandbox directory
- Runtime files exist after create
- Environment actions work immediately after create
- No environment card survives failed provisioning
- Runtime status reflects real sandbox existence
- Environment metadata references real sandbox ids
- No fake runtime states remain possible