from workout_calories import estimate_calories_burned, is_cardio


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


def test_negative_duration():
    assert estimate_calories_burned("run", -10, 70) == 0.0


def test_whitespace_stripped():
    assert estimate_calories_burned("  run  ", 30, 70) == estimate_calories_burned("run", 30, 70)


# --- is_cardio ---

def test_is_cardio_running():
    assert is_cardio("run") is True
    assert is_cardio("running") is True


def test_is_cardio_cycling():
    assert is_cardio("cycling") is True
    assert is_cardio("bike") is True


def test_is_cardio_swimming():
    assert is_cardio("swim") is True
    assert is_cardio("swimming") is True


def test_is_cardio_walking():
    assert is_cardio("walk") is True
    assert is_cardio("walking") is True


def test_is_cardio_rowing():
    assert is_cardio("rowing") is True


def test_is_cardio_elliptical():
    assert is_cardio("elliptical") is True


def test_is_not_cardio_weights():
    assert is_cardio("weights") is False
    assert is_cardio("strength") is False


def test_is_not_cardio_hiit():
    assert is_cardio("hiit") is False


def test_is_not_cardio_yoga():
    assert is_cardio("yoga") is False


def test_is_cardio_case_insensitive():
    assert is_cardio("RUN") is True
    assert is_cardio("Swimming") is True


def test_is_cardio_whitespace():
    assert is_cardio("  cycling  ") is True


def test_is_cardio_unknown():
    assert is_cardio("zumba") is False
