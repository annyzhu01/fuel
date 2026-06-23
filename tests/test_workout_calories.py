from workout_calories import estimate_calories_burned


def test_running_30min():
    result = estimate_calories_burned("run", 30, 70)
    assert 280 <= result <= 400


def test_weights_45min():
    result = estimate_calories_burned("weights", 45, 70)
    assert 180 <= result <= 320


def test_unknown_exercise_defaults():
    result = estimate_calories_burned("zumba", 30, 70)
    assert result > 0


def test_zero_duration():
    result = estimate_calories_burned("run", 0, 70)
    assert result == 0.0


def test_legs_day():
    result = estimate_calories_burned("legs", 60, 70)
    assert result > 0


def test_case_insensitive():
    assert estimate_calories_burned("RUN", 30, 70) == estimate_calories_burned("run", 30, 70)
