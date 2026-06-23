from query_recipes import query_recipes, query_meal

DAILY_CALORIES = 1800
BREAKFAST_CAL = 400
LUNCH_CAL = 500
DINNER_MAIN_CAL = 400
DINNER_SIDE_CAL = 200
DESSERT_CAL = 300

DAILY_PROTEIN = 120
BREAKFAST_PROTEIN = 30
LUNCH_PROTEIN = 35
DINNER_PROTEIN = 40
DESSERT_PROTEIN = 10

USER_INGREDIENTS = ["chicken", "oats", "egg whites", "wraps", "peanut butter"]


def print_recipes(label: str, recipes: list[dict]):
    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print('=' * 50)
    if not recipes:
        print("  No results.")
        return
    for r in recipes:
        sim = f"[{r['similarity']:.3f}]" if r.get("similarity") is not None else ""
        cal = f"{r['calories']:.0f} kcal" if r.get("calories") else "? kcal"
        protein = f"{r['protein_g']:.0f}g protein" if r.get("protein_g") else ""
        macros = ", ".join(filter(None, [cal, protein]))
        print(f"  {sim} {r['title']} ({macros})  [{r.get('category', '')}]")
        if r.get("description"):
            print(f"     {r['description'][:100]}")


def test_basic_search():
    print("\n\n### BASIC SEARCH ###")
    for query in ["slow cooker beef brisket", "breakfast with oats"]:
        results = query_recipes(query, match_count=5)
        print_recipes(f"Query: '{query}'", results)


def test_category_filter():
    print("\n\n### CATEGORY FILTER ###")
    results = query_recipes("stir fry vegetables", match_count=5, filter_category="side-dish")
    print_recipes("Side dishes: stir fry vegetables", results)

    results = query_recipes("grilled chicken", match_count=5, filter_category="main-dish")
    print_recipes("Main dishes: grilled chicken", results)


def test_meal_pairing():
    print("\n\n### MEAL PAIRING ###")
    meal = query_meal(
        main_query="grilled chicken or fish",
        side_query="roasted vegetables or salad",
        mains_count=3,
        sides_count=3,
        max_calories=DINNER_MAIN_CAL,
    )
    print_recipes("MAINS", meal["mains"])
    print_recipes("SIDES", meal["sides"])
    print(f"\n  Target dinner total: ~{DINNER_MAIN_CAL + DINNER_SIDE_CAL} kcal")


def test_daily_plan():
    ingredients_str = ", ".join(USER_INGREDIENTS)
    print("\n\n### 1800 CAL DAILY PLAN ###")
    print(f"  Target: {DAILY_CALORIES} kcal | {DAILY_PROTEIN}g protein")
    print(f"  Ingredients at home: {ingredients_str}")
    print(f"  Breakdown: Breakfast ~{BREAKFAST_CAL} kcal/{BREAKFAST_PROTEIN}g | Lunch ~{LUNCH_CAL} kcal/{LUNCH_PROTEIN}g | Dinner ~{DINNER_MAIN_CAL + DINNER_SIDE_CAL} kcal/{DINNER_PROTEIN}g | Dessert ~{DESSERT_CAL} kcal/{DESSERT_PROTEIN}g\n")

    breakfast = query_recipes(
        "high protein breakfast oats egg whites",
        match_count=3,
        max_calories=BREAKFAST_CAL,
        min_protein=BREAKFAST_PROTEIN,
    )
    print_recipes(f"BREAKFAST (target: {BREAKFAST_CAL} kcal / {BREAKFAST_PROTEIN}g protein)", breakfast)

    lunch = query_recipes(
        "chicken wrap high protein filling lunch",
        match_count=3,
        max_calories=LUNCH_CAL,
        min_protein=LUNCH_PROTEIN,
    )
    print_recipes(f"LUNCH (target: {LUNCH_CAL} kcal / {LUNCH_PROTEIN}g protein)", lunch)

    dinner = query_meal(
        main_query="chicken breast lean protein dinner",
        side_query="roasted or steamed vegetables",
        mains_count=3,
        sides_count=3,
        max_calories=DINNER_MAIN_CAL,
        min_protein=DINNER_PROTEIN,
    )
    print_recipes(f"DINNER MAINS (target: {DINNER_MAIN_CAL} kcal / {DINNER_PROTEIN}g protein)", dinner["mains"])
    print_recipes(f"DINNER SIDES (target: {DINNER_SIDE_CAL} kcal)", dinner["sides"])

    dessert = query_recipes(
        "peanut butter protein dessert snack",
        match_count=3,
        max_calories=DESSERT_CAL,
        min_protein=DESSERT_PROTEIN,
    )
    print_recipes(f"DESSERT (target: {DESSERT_CAL} kcal / {DESSERT_PROTEIN}g protein)", dessert)


if __name__ == "__main__":
    test_basic_search()
    test_category_filter()
    test_meal_pairing()
    test_daily_plan()
