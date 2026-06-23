from daily_plan import _compute_remaining


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
    result = _compute_remaining(target, 400, food_logged)
    assert result["remaining_calories"] == 1700.0   # 1800 + 400 - 500
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
