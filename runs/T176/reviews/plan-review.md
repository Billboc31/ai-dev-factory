# T176 — Plan Review

## Verdict

The plan correctly addresses the redeploy failure: redeploy must not assume that `sandbox_dir/source` is still present and valid. It should detect a missing or incomplete source clone, rehydrate it, and only then resolve `.ai-dev-factory/scripts`.

This is the right backend fix for the observed error:

```text
runtime mismatch: scripts directory not found at <sandbox>/source/.ai-dev-factory/scripts
```

## What is good

- Adds explicit source clone validation before script resolution.
- Adds automatic rehydration when `source/`, `.git`, or `.ai-dev-factory/scripts` is missing.
- Adds a `force_source_refresh` option.
- Keeps the default create flow automatic.
- Adds UI affordance for advanced runtime options.

## Main issue

The plan currently adds `runtime_root` to the UI/API request but explicitly excludes backend wiring of the runtime root override.

That means the UI may appear to let the user choose a runtime root, while the backend still ignores it. This would create a misleading UX and repeat the same confusion this ticket is trying to remove.

## Required correction

Do not ship a non-functional `runtime_root` override.

Either:

1. fully wire `runtime_root` end-to-end in this ticket; or
2. remove/disable the `runtime_root` input from this ticket and only keep `force_source_refresh`.

The preferred option is to wire it properly because the original issue asks for choosing the path from the UI when needed.

## Final recommendation

Approve the plan only after adding backend handling for `runtime_root` override, including validation and persistence.