from unittest.mock import patch, MagicMock
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def _make_search_response(search_call_num):
    """Simulate Claude calling search_recipes."""
    tool_use = MagicMock()
    tool_use.type = "tool_use"
    tool_use.name = "search_recipes"
    tool_use.id = f"search_{search_call_num}"
    tool_use.input = {"query": f"high protein meal {search_call_num}", "slot": "dinner"}
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_use]
    return response


def _make_budget_return_value():
    return {
        "target": {"base_calories": 1800, "goal_protein_g": 160, "goal_carbs_g": 200, "goal_fat_g": 60},
        "workout_burn": 0,
        "remaining": {
            "remaining_calories": 500,
            "remaining_protein_g": 42,
            "remaining_carbs_g": 50,
            "remaining_fat_g": 15,
            "slots_needed": ["breakfast", "lunch", "dinner", "snack"],
        },
    }


@patch("daily_plan_agentic.query_recipes", return_value=[])
@patch("daily_plan_agentic.get_pantry", return_value=[])
@patch("daily_plan_agentic.get_daily_budget")
@patch("daily_plan_agentic._get_claude")
def test_search_budget_capped_at_max(mock_claude, mock_budget, mock_pantry, mock_query):
    """After MAX_SEARCH_CALLS searches, Claude must call submit_plan, not a 5th search."""
    from daily_plan_agentic import build_daily_plan_agentic, MAX_SEARCH_CALLS

    mock_budget.return_value = _make_budget_return_value()

    plan_item = {"slot": "dinner", "recipe_id": None, "recipe_name": "Protein Shake",
                 "calories": 200, "protein_g": 40, "carbs_g": 5, "fat_g": 2, "reason": "budget exhausted"}

    # Claude calls search_recipes MAX_SEARCH_CALLS times, then submit_plan
    search_responses = [_make_search_response(i + 1) for i in range(MAX_SEARCH_CALLS)]
    submit_response = _make_submit_response([plan_item])
    mock_claude.return_value.messages.create.side_effect = search_responses + [submit_response]

    result = build_daily_plan_agentic("mvp-user", "2026-06-24", [])

    # Verify submit_plan was called (result has plan key)
    assert "plan" in result

    # Verify total calls: MAX_SEARCH_CALLS search rounds + 1 submit round
    total_calls = mock_claude.return_value.messages.create.call_count
    assert total_calls == MAX_SEARCH_CALLS + 1, (
        f"Expected {MAX_SEARCH_CALLS + 1} Claude calls, got {total_calls}"
    )

    # Verify the last user message before submit contains the budget exhausted text
    last_call_messages = mock_claude.return_value.messages.create.call_args_list[-1][1]["messages"]
    # Find the last user message
    last_user_msg = next(
        m for m in reversed(last_call_messages) if m["role"] == "user"
    )
    assert isinstance(last_user_msg["content"], list), "Budget exhausted msg should be in tool_results list"
    texts = [c.get("text", "") for c in last_user_msg["content"] if isinstance(c, dict)]
    assert any("budget exhausted" in t.lower() for t in texts), (
        f"Expected budget exhaustion text in last user message, got: {texts}"
    )

    # Verify query_recipes was called exactly MAX_SEARCH_CALLS times
    assert mock_query.call_count == MAX_SEARCH_CALLS
