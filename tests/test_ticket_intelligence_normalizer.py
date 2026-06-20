"""Unit tests for _normalize() and _extract_json() in ticket_intelligence_analyzer (T197)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from ticket_intelligence_analyzer import _extract_json, _normalize

_COMPUTED = {"estimated_token_size": 4000}


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json_object(self):
        text = '{"difficulty_score": 5, "risk_score": 3}'
        result = _extract_json(text)
        assert result["difficulty_score"] == 5

    def test_json_in_markdown_fence(self):
        text = '```json\n{"difficulty_score": 7}\n```'
        result = _extract_json(text)
        assert result["difficulty_score"] == 7

    def test_json_in_plain_fence(self):
        text = '```\n{"difficulty_score": 4}\n```'
        result = _extract_json(text)
        assert result["difficulty_score"] == 4

    def test_json_preceded_by_free_text(self):
        text = "Here is the analysis:\n\n{\"difficulty_score\": 6, \"risk_score\": 5}"
        result = _extract_json(text)
        assert result["difficulty_score"] == 6

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _extract_json("")

    def test_non_json_text_raises(self):
        with pytest.raises(ValueError):
            _extract_json("This is just a plain sentence with no JSON.")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json("{difficulty_score: 5}")

    def test_json_with_surrounding_whitespace(self):
        text = '  \n  {"risk_score": 8}  \n  '
        result = _extract_json(text)
        assert result["risk_score"] == 8

    def test_fence_with_malformed_json_falls_through_to_regex(self):
        # Malformed fence but valid JSON later in text — should extract via regex
        text = "```json\nnot json\n```\n{\"difficulty_score\": 2}"
        result = _extract_json(text)
        assert result["difficulty_score"] == 2


# ---------------------------------------------------------------------------
# _normalize — score clamping
# ---------------------------------------------------------------------------

class TestNormalizeScoreClamping:
    def test_difficulty_score_below_min_clamped_to_1(self):
        result = _normalize({"difficulty_score": 0}, _COMPUTED)
        assert result["difficulty_score"] == 1

    def test_difficulty_score_above_max_clamped_to_10(self):
        result = _normalize({"difficulty_score": 11}, _COMPUTED)
        assert result["difficulty_score"] == 10

    def test_difficulty_score_within_range_preserved(self):
        result = _normalize({"difficulty_score": 7}, _COMPUTED)
        assert result["difficulty_score"] == 7

    def test_difficulty_score_missing_defaults_to_5(self):
        result = _normalize({}, _COMPUTED)
        assert result["difficulty_score"] == 5

    def test_difficulty_score_none_defaults_to_5(self):
        result = _normalize({"difficulty_score": None}, _COMPUTED)
        assert result["difficulty_score"] == 5

    def test_difficulty_score_invalid_string_defaults_to_5(self):
        result = _normalize({"difficulty_score": "high"}, _COMPUTED)
        assert result["difficulty_score"] == 5

    def test_risk_score_below_min_clamped_to_1(self):
        result = _normalize({"risk_score": -3}, _COMPUTED)
        assert result["risk_score"] == 1

    def test_risk_score_above_max_clamped_to_10(self):
        result = _normalize({"risk_score": 99}, _COMPUTED)
        assert result["risk_score"] == 10

    def test_risk_score_missing_defaults_to_5(self):
        result = _normalize({}, _COMPUTED)
        assert result["risk_score"] == 5


# ---------------------------------------------------------------------------
# _normalize — difficulty_label auto-derivation
# ---------------------------------------------------------------------------

class TestNormalizeDifficultyLabel:
    @pytest.mark.parametrize("score,expected_label", [
        (1, "trivial"),
        (2, "trivial"),
        (3, "simple"),
        (4, "simple"),
        (5, "medium"),
        (6, "medium"),
        (7, "complex"),
        (8, "complex"),
        (9, "critical"),
        (10, "critical"),
    ])
    def test_auto_derived_from_score(self, score, expected_label):
        result = _normalize({"difficulty_score": score}, _COMPUTED)
        assert result["difficulty_label"] == expected_label

    def test_explicit_label_preserved(self):
        result = _normalize({"difficulty_score": 5, "difficulty_label": "medium"}, _COMPUTED)
        assert result["difficulty_label"] == "medium"


# ---------------------------------------------------------------------------
# _normalize — autonomous_execution_recommendation
# ---------------------------------------------------------------------------

class TestNormalizeAutonomousRec:
    @pytest.mark.parametrize("valid_val", [
        "safe", "plan_review_required", "human_review_required", "not_recommended"
    ])
    def test_valid_values_preserved(self, valid_val):
        result = _normalize({"autonomous_execution_recommendation": valid_val}, _COMPUTED)
        assert result["autonomous_execution_recommendation"] == valid_val

    def test_invalid_value_falls_back_to_plan_review_required(self):
        result = _normalize({"autonomous_execution_recommendation": "do_whatever"}, _COMPUTED)
        assert result["autonomous_execution_recommendation"] == "plan_review_required"

    def test_none_falls_back_to_plan_review_required(self):
        result = _normalize({"autonomous_execution_recommendation": None}, _COMPUTED)
        assert result["autonomous_execution_recommendation"] == "plan_review_required"

    def test_missing_falls_back_to_plan_review_required(self):
        result = _normalize({}, _COMPUTED)
        assert result["autonomous_execution_recommendation"] == "plan_review_required"


# ---------------------------------------------------------------------------
# _normalize — cost estimation fallback
# ---------------------------------------------------------------------------

class TestNormalizeCostEstimation:
    def test_cost_present_in_raw_is_preserved(self):
        raw = {
            "estimated_cost_min": 0.10,
            "estimated_cost_max": 0.20,
            "cost_estimate_status": "estimated",
            "recommended_model": "balanced-code-model",
        }
        result = _normalize(raw, _COMPUTED)
        assert result["estimated_cost_min"] == 0.10
        assert result["estimated_cost_max"] == 0.20
        assert result["cost_estimate_status"] == "estimated"

    def test_cost_computed_when_missing(self):
        raw = {"recommended_model": "balanced-code-model"}
        result = _normalize(raw, _COMPUTED)
        assert result["estimated_cost_min"] is not None
        assert result["estimated_cost_max"] is not None
        assert result["cost_estimate_status"] == "estimated"

    def test_cost_unknown_when_model_not_in_catalog(self):
        raw = {"recommended_model": "unknown-model-xyz"}
        result = _normalize(raw, _COMPUTED)
        assert result["estimated_cost_min"] is None
        assert result["estimated_cost_max"] is None
        assert result["cost_estimate_status"] == "unknown"

    def test_cost_computed_when_only_min_missing(self):
        raw = {
            "estimated_cost_max": 0.50,
            "recommended_model": "balanced-code-model",
        }
        result = _normalize(raw, _COMPUTED)
        # cost_min was None → estimate_cost() called → both replaced
        assert result["estimated_cost_min"] is not None
        assert result["cost_estimate_status"] == "estimated"

    def test_free_model_has_zero_cost(self):
        raw = {"recommended_model": "local-qwen"}
        result = _normalize(raw, _COMPUTED)
        assert result["estimated_cost_min"] == 0.0
        assert result["estimated_cost_max"] == 0.0


# ---------------------------------------------------------------------------
# _normalize — list fields
# ---------------------------------------------------------------------------

class TestNormalizeListFields:
    def test_complexity_factors_list_serialized_to_json(self):
        raw = {"complexity_factors": ["backend", "database"]}
        result = _normalize(raw, _COMPUTED)
        assert result["complexity_factors"] == json.dumps(["backend", "database"])

    def test_complexity_factors_non_list_becomes_empty(self):
        result = _normalize({"complexity_factors": "backend"}, _COMPUTED)
        assert result["complexity_factors"] == json.dumps([])

    def test_complexity_factors_none_becomes_empty(self):
        result = _normalize({"complexity_factors": None}, _COMPUTED)
        assert result["complexity_factors"] == json.dumps([])

    def test_complexity_factors_missing_becomes_empty(self):
        result = _normalize({}, _COMPUTED)
        assert result["complexity_factors"] == json.dumps([])

    def test_dependency_hints_list_serialized_to_json(self):
        raw = {"dependency_hints": ["T001", "T042"]}
        result = _normalize(raw, _COMPUTED)
        assert result["dependency_hints"] == json.dumps(["T001", "T042"])

    def test_dependency_hints_non_list_becomes_empty(self):
        result = _normalize({"dependency_hints": "T001"}, _COMPUTED)
        assert result["dependency_hints"] == json.dumps([])

    def test_dependency_hints_dict_becomes_empty(self):
        result = _normalize({"dependency_hints": {"ticket": "T001"}}, _COMPUTED)
        assert result["dependency_hints"] == json.dumps([])


# ---------------------------------------------------------------------------
# _normalize — queue_rank coercion
# ---------------------------------------------------------------------------

class TestNormalizeQueueRank:
    def test_integer_queue_rank_preserved(self):
        result = _normalize({"queue_rank": 20}, _COMPUTED)
        assert result["queue_rank"] == 20

    def test_string_queue_rank_coerced_to_int(self):
        result = _normalize({"queue_rank": "15"}, _COMPUTED)
        assert result["queue_rank"] == 15

    def test_invalid_queue_rank_becomes_none(self):
        result = _normalize({"queue_rank": "high"}, _COMPUTED)
        assert result["queue_rank"] is None

    def test_none_queue_rank_stays_none(self):
        result = _normalize({"queue_rank": None}, _COMPUTED)
        assert result["queue_rank"] is None

    def test_missing_queue_rank_is_none(self):
        result = _normalize({}, _COMPUTED)
        assert result["queue_rank"] is None


# ---------------------------------------------------------------------------
# _normalize — boolean fields
# ---------------------------------------------------------------------------

class TestNormalizeBooleanFields:
    def test_parallel_safe_candidate_true(self):
        result = _normalize({"parallel_safe_candidate": True}, _COMPUTED)
        assert result["parallel_safe_candidate"] == 1

    def test_parallel_safe_candidate_false(self):
        result = _normalize({"parallel_safe_candidate": False}, _COMPUTED)
        assert result["parallel_safe_candidate"] == 0

    def test_requires_human_plan_review_true(self):
        result = _normalize({"requires_human_plan_review": True}, _COMPUTED)
        assert result["requires_human_plan_review"] == 1

    def test_requires_human_code_review_false(self):
        result = _normalize({"requires_human_code_review": False}, _COMPUTED)
        assert result["requires_human_code_review"] == 0


# ---------------------------------------------------------------------------
# _normalize — full round-trip with a realistic payload
# ---------------------------------------------------------------------------

class TestNormalizeFullPayload:
    def test_full_payload_produces_expected_keys(self):
        raw = {
            "difficulty_score": 6,
            "difficulty_label": "medium",
            "risk_score": 5,
            "risk_label": "moderate",
            "complexity_factors": ["backend", "database", "UI"],
            "recommended_model": "advanced-reasoning-model",
            "recommended_model_reason": "Requires architecture reasoning.",
            "estimated_input_tokens": 12000,
            "estimated_output_tokens": 6000,
            "estimated_cost_min": 0.05,
            "estimated_cost_max": 0.35,
            "cost_currency": "USD",
            "cost_estimate_status": "estimated",
            "queue_rank": 20,
            "queue_reason": "Backend foundation first.",
            "dependency_hints": ["T001"],
            "parallel_safe_candidate": False,
            "requires_human_plan_review": True,
            "human_plan_review_reason": "DB schema change.",
            "requires_human_code_review": False,
            "human_code_review_reason": None,
            "autonomous_execution_recommendation": "plan_review_required",
            "analysis_summary": "Medium difficulty, moderate risk.",
        }
        result = _normalize(raw, _COMPUTED)

        assert result["difficulty_score"] == 6
        assert result["difficulty_label"] == "medium"
        assert result["risk_score"] == 5
        assert result["risk_label"] == "moderate"
        assert result["recommended_model"] == "advanced-reasoning-model"
        assert result["queue_rank"] == 20
        assert result["autonomous_execution_recommendation"] == "plan_review_required"
        assert result["requires_human_plan_review"] == 1
        assert result["requires_human_code_review"] == 0
        assert result["parallel_safe_candidate"] == 0
        assert result["analysis_summary"] == "Medium difficulty, moderate risk."
        assert json.loads(result["complexity_factors"]) == ["backend", "database", "UI"]
        assert json.loads(result["dependency_hints"]) == ["T001"]
