# Plan review — T138

Decision: PLAN_FIX_REQUIRED

The reduced dry-run proposal scope is now appropriate.

However, the current plan still hardcodes:

- ANTHROPIC_API_KEY
- AI_DEV_FACTORY_MODEL
- Claude-specific integration assumptions

This violates the generic runtime architecture.

The auto-fix proposal workflow must use the configured AI runtime abstraction already used elsewhere in the platform.

The implementation must NOT directly depend on:

- Anthropic APIs
- Claude-specific request formats
- ai-dev-factory-specific runtime assumptions

See `runs/T138/fixes/plan-fix-2.md`.
