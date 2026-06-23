_MET = {
    "run": 9.8,
    "running": 9.8,
    "jog": 7.0,
    "jogging": 7.0,
    "walk": 3.5,
    "walking": 3.5,
    "cycling": 7.5,
    "bike": 7.5,
    "swim": 8.0,
    "swimming": 8.0,
    "weights": 5.0,
    "strength": 5.0,
    "hiit": 10.0,
    "yoga": 2.5,
    "pilates": 3.0,
    "rowing": 8.5,
    "elliptical": 5.0,
    "crossfit": 9.0,
    "legs": 5.0,
    "push": 4.5,
    "pull": 4.5,
}

_DEFAULT_MET = 5.0


def estimate_calories_burned(
    exercise_type: str,
    duration_minutes: float,
    user_weight_kg: float,
) -> float:
    """MET-based calorie burn: MET * weight_kg * hours."""
    if duration_minutes <= 0:
        return 0.0
    met = _MET.get(exercise_type.lower().strip(), _DEFAULT_MET)
    hours = duration_minutes / 60
    return round(met * user_weight_kg * hours, 1)
