# Plan fix — T138 runtime abstraction

## Required change

Replace provider-specific AI integration with the generic configured AI runtime abstraction already used elsewhere in the platform.

The implementation must NOT directly depend on:

- Anthropic APIs
- Claude-specific payloads
- hardcoded provider environment variables
- ai-dev-factory-specific model assumptions

---

# Required updates

## Generic AI runtime integration

Replace:

- ANTHROPIC_API_KEY
- AI_DEV_FACTORY_MODEL
- direct Claude Messages API calls

with:

- the configured AI runtime abstraction
- runtime-configurable providers/models
- generic request/response handling

The proposer must work with:

- local runtimes
- hosted runtimes
- future providers

without changing orchestrator logic.

## Generic proposal contract

The orchestrator should only depend on:

- prompt input
- structured proposal output

The provider/runtime implementation details must remain isolated behind the runtime abstraction.

## Acceptance criteria

- no direct Anthropic-specific integration exists in the proposer/orchestrator
- no hardcoded Claude model assumptions exist
- AI provider/runtime can be swapped without changing proposal orchestration
- proposal workflow remains generic and project-agnostic
