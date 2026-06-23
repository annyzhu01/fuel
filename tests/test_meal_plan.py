from query_recipes import query_recipes, generate_response

# Meal plan constraints
# Target: ~1800 cal total, ~120g protein total, budget-friendly
# Available: chicken breast, wraps, zucchini, apple, kiwi, oats, peanut butter

MEALS = [
    {
        "name": "Breakfast",
        "query": "oatmeal with peanut butter high protein breakfast",
        "cal_budget": (300, 500),
        "protein_budget": (15, 30),
    },
    {
        "name": "Lunch",
        "query": "chicken wrap with vegetables light lunch",
        "cal_budget": (400, 600),
        "protein_budget": (30, 50),
    },
    {
        "name": "Dinner",
        "query": "chicken breast with zucchini healthy dinner",
        "cal_budget": (400, 650),
        "protein_budget": (35, 55),
    },
    {
        "name": "Dessert",
        "query": "apple kiwi fruit dessert light sweet",
        "cal_budget": (100, 300),
        "protein_budget": (2, 15),
    },
]


def plan_meals():
    all_meals = {}
    for meal in MEALS:
        min_cal, max_cal = meal["cal_budget"]
        min_protein, max_protein = meal["protein_budget"]
        results = query_recipes(
            meal["query"],
            match_count=5,
            min_calories=min_cal,
            max_calories=max_cal,
            min_protein=min_protein,
            max_protein=max_protein,
        )
        all_meals[meal["name"]] = results
        print(f"{meal['name']}: {len(results)} candidates")

    user_query = (
        "Create a budget-friendly meal plan with breakfast, lunch, dinner, and dessert "
        "totalling around 1800 calories and 120g protein. "
        "I have chicken breast, wraps, zucchini, apple, kiwi, oats, and peanut butter."
    )

    flat_recipes = []
    for slot, recipes in all_meals.items():
        for r in recipes:
            r["_slot"] = slot
            flat_recipes.append(r)

    context_lines = []
    for slot, recipes in all_meals.items():
        context_lines.append(f"\n{slot.upper()} OPTIONS:")
        for i, r in enumerate(recipes, 1):
            line = f"  {i}. {r['title']}"
            macros = []
            if r.get("calories") is not None:
                macros.append(f"{r['calories']:.0f} kcal")
            if r.get("protein_g") is not None:
                macros.append(f"{r['protein_g']:.0f}g protein")
            if r.get("fat_g") is not None:
                macros.append(f"{r['fat_g']:.0f}g fat")
            if r.get("carbohydrate_g") is not None:
                macros.append(f"{r['carbohydrate_g']:.0f}g carbs")
            if macros:
                line += f" ({', '.join(macros)})"
            context_lines.append(line)

    context = "\n".join(context_lines)

    from utils import get_supabase_client
    import anthropic, os
    from dotenv import load_dotenv
    load_dotenv()
    claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=(
            "You are a budget-friendly meal planning assistant. "
            "Pick one recipe per meal slot from the options provided. "
            "Show the full day plan with each meal's macros and a combined daily total. "
            "Be concise."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"User request: {user_query}\n\n"
                    f"Available recipes by slot:{context}\n\n"
                    "Build the best daily meal plan from these options."
                ),
            }
        ],
    )
    print("\n" + "=" * 60)
    print(response.content[0].text)


if __name__ == "__main__":
    plan_meals()
