All three fixes are applied and verified. Here's a summary:

**P1 — `sandbox_runtime_deploy.py`:** Removed the dead guard (`source_path.is_relative_to(sandbox_dir)` which was always `True` by construction). Replaced with a real existence check on `script_source.is_dir()` after `script_source` is defined — now raises `RuntimeError` if the `.ai-dev-factory/scripts` directory is missing from the sandbox source clone.

**P2 — `CreateEnvironmentModal.jsx`:** Wrapped the project-ID branch in a fragment, added the "Runtime target" block after the branch selector showing all three fields as `(auto-assigned)`.

**P3 — `CreateEnvironmentModal.jsx`:** Replaced all `not-font-mono` (invalid Tailwind) with `font-sans` on the 3 label spans in both flows.
