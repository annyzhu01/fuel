from daily_plan import _compute_remaining, _deduplicate_plan


def test_compute_remaining_no_logs():
    target = {"base_calories": 1800, "goal_protein_g": 120, "goal_carbs_g": 200, "goal_fat_g": 60}
    result = _compute_remaining(target, 0, [])
    assert result["remaining_calories"] == 1800
    assert result["remaining_protein_g"] == 120
    assert result["remaining_carbs_g"] == 200
    assert result["remaining_fat_g"] == 60
    assert result["slots_needed"] == ["breakfast", "lunch", "dinner", "snack"]


def test_compute_remaining_with_workout_and_meal():
    target = {"base_calories": 1800, "goal_protein_g": 120, "goal_carbs_g": 200, "goal_fat_g": 60}
    food_logged = [
        {"meal_slot": "breakfast", "calories": 500, "protein_g": 30, "carbs_g": 55, "fat_g": 14}
    ]
    # 400 kcal cardio burn >300 → add 50% (200). weights burn ignored.
    result = _compute_remaining(target, 400, food_logged, cardio_burn=400)
    assert result["remaining_calories"] == 1500.0   # 1800 + 200 - 500
    assert result["remaining_protein_g"] == 90.0    # 120 - 30
    assert "breakfast" not in result["slots_needed"]
    assert "lunch" in result["slots_needed"]


def test_all_slots_logged():
    target = {"base_calories": 1800, "goal_protein_g": 120, "goal_carbs_g": 200, "goal_fat_g": 60}
    food_logged = [
        {"meal_slot": s, "calories": 400, "protein_g": 25, "carbs_g": 45, "fat_g": 12}
        for s in ["breakfast", "lunch", "dinner", "snack"]
    ]
    result = _compute_remaining(target, 0, food_logged)
    assert result["slots_needed"] == []
    assert result["remaining_calories"] == 200.0  # 1800 - 1600


# --- _deduplicate_plan tests ---


def test_deduplicate_plan_no_duplicates():
    plan = [
        {"slot": "breakfast", "recipe_id": "aaa", "recipe_name": "Eggs"},
        {"slot": "lunch", "recipe_id": "bbb", "recipe_name": "Chicken"},
    ]
    result = _deduplicate_plan(plan, {})
    assert [item["recipe_id"] for item in result] == ["aaa", "bbb"]


def test_deduplicate_plan_replaces_duplicate_with_candidate():
    plan = [
        {"slot": "breakfast", "recipe_id": "aaa", "recipe_name": "Eggs"},
        {"slot": "lunch", "recipe_id": "aaa", "recipe_name": "Eggs"},
    ]
    candidates_by_slot = {
        "lunch": [
            {"id": "aaa", "title": "Eggs", "calories": 300, "protein_g": 20, "carbohydrate_g": 10, "fat_g": 15},
            {"id": "ccc", "title": "Salad", "calories": 250, "protein_g": 15, "carbohydrate_g": 20, "fat_g": 10},
        ],
    }
    result = _deduplicate_plan(plan, candidates_by_slot)
    assert result[0]["recipe_id"] == "aaa"
    assert result[1]["recipe_id"] == "ccc"
    assert result[1]["recipe_name"] == "Salad"


def test_deduplicate_plan_clears_id_when_no_candidate():
    plan = [
        {"slot": "breakfast", "recipe_id": "aaa", "recipe_name": "Eggs"},
        {"slot": "lunch", "recipe_id": "aaa", "recipe_name": "Eggs"},
    ]
    result = _deduplicate_plan(plan, {})
    assert result[0]["recipe_id"] == "aaa"
    assert result[1]["recipe_id"] is None


def test_deduplicate_plan_skips_none_recipe_ids():
    plan = [
        {"slot": "breakfast", "recipe_id": None, "recipe_name": "Yogurt"},
        {"slot": "lunch", "recipe_id": None, "recipe_name": "Shake"},
    ]
    result = _deduplicate_plan(plan, {})
    assert len(result) == 2
    assert result[0]["recipe_id"] is None
    assert result[1]["recipe_id"] is None
