"""Configurable model catalog for Ticket Intelligence cost estimation.

Maps logical model names to cost-per-token pricing hints (USD per 1K tokens).
No provider-specific imports or routing logic — purely advisory.
"""

from __future__ import annotations

MODEL_CATALOG: dict[str, dict] = {
    "local-qwen": {
        "input_cost_per_1k": 0.0,
        "output_cost_per_1k": 0.0,
    },
    "cheap-fast-model": {
        "input_cost_per_1k": 0.0003,
        "output_cost_per_1k": 0.0006,
    },
    "balanced-code-model": {
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
    },
    "advanced-reasoning-model": {
        "input_cost_per_1k": 0.015,
        "output_cost_per_1k": 0.075,
    },
}


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> tuple[float | None, float | None, str]:
    """Return (cost_min, cost_max, status) for a model and token counts.

    Applies a ±20% band around the base estimate for min/max.
    Returns status='unknown' when the model is not in the catalog.
    """
    entry = MODEL_CATALOG.get(model)
    if entry is None:
        return None, None, "unknown"

    base = (
        entry["input_cost_per_1k"] * input_tokens / 1000
        + entry["output_cost_per_1k"] * output_tokens / 1000
    )
    return round(base * 0.8, 4), round(base * 1.2, 4), "estimated"
