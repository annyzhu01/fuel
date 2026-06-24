from unittest.mock import patch, MagicMock
import json


def _make_submit_response(plan_items):
    """Simulate Claude calling submit_plan."""
    tool_use = MagicMock()
    tool_use.type = "tool_use"
    tool_use.name = "submit_plan"
    tool_use.id = "tool_123"
    tool_use.input = {
        "plan": plan_items,
        "total_planned": {"calories": 500, "protein_g": 42, "carbs_g": 50, "fat_g": 15},
        "protein_gap": 0,
        "protein_warning": None,
        "coach_note": "Good plan."
    }
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_use]
    return response


@patch("daily_plan_agentic.get_pantry", return_value=["chicken breast", "eggs"])
@patch("daily_plan_agentic.get_daily_budget")
@patch("daily_plan_agentic._get_claude")
def test_agentic_plan_returns_on_submit(mock_claude, mock_budget, mock_pantry):
    mock_budget.return_value = {
        "target": {"base_calories": 1800, "goal_protein_g": 160, "goal_carbs_g": 200, "goal_fat_g": 60},
        "workout_burn": 0,
        "remaining": {
            "remaining_calories": 500,
            "remaining_protein_g": 42,
            "remaining_carbs_g": 50,
            "remaining_fat_g": 15,
            "slots_needed": ["dinner"],
        },
    }
    plan_item = {"slot": "dinner", "recipe_id": "abc", "recipe_name": "Chicken Rice",
                 "calories": 500, "protein_g": 42, "carbs_g": 50, "fat_g": 15, "reason": "high protein"}
    mock_claude.return_value.messages.create.return_value = _make_submit_response([plan_item])

    from daily_plan_agentic import build_daily_plan_agentic
    result = build_daily_plan_agentic("mvp-user", "2026-06-24", [])

    assert "plan" in result
    assert len(result["plan"]) == 1
    assert result["plan"][0]["recipe_name"] == "Chicken Rice"
    assert result["protein_gap"] == 0


@patch("daily_plan_agentic.get_pantry", return_value=[])
@patch("daily_plan_agentic.get_daily_budget")
def test_agentic_all_slots_logged(mock_budget, mock_pantry):
    mock_budget.return_value = {
        "target": {"base_calories": 1800, "goal_protein_g": 160, "goal_carbs_g": 200, "goal_fat_g": 60},
        "workout_burn": 0,
        "remaining": {
            "remaining_calories": 0,
            "remaining_protein_g": 0,
            "remaining_carbs_g": 0,
            "remaining_fat_g": 0,
            "slots_needed": [],
        },
    }
    from daily_plan_agentic import build_daily_plan_agentic
    result = build_daily_plan_agentic("mvp-user", "2026-06-24", [])
    assert result["plan"] == []
    assert "message" in result
