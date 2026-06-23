import anthropic
import os
from utils import get_supabase_client
from sentence_transformers import SentenceTransformer

_clients = None

def _get_clients():
    global _clients
    if _clients is None:
        _clients = (
            get_supabase_client(),
            SentenceTransformer("all-MiniLM-L6-v2"),
            anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY")),
        )
    return _clients


def query_recipes(
    semantic_query: str,
    match_count: int = 10,
    min_calories: float = None,
    max_calories: float = None,
    min_protein: float = None,
    max_protein: float = None,
    min_carbs: float = None,
    max_carbs: float = None,
    min_fat: float = None,
    max_fat: float = None,
    filter_category: str = None,
):
    supabase, model, _ = _get_clients()
    query_vector = model.encode(semantic_query).tolist()

    params = {
        "query_embedding": query_vector,
        "match_count": match_count,
        "min_calories": min_calories,
        "max_calories": max_calories,
        "min_protein": min_protein,
        "max_protein": max_protein,
        "min_carbs": min_carbs,
        "max_carbs": max_carbs,
        "min_fat": min_fat,
        "max_fat": max_fat,
        "filter_category": filter_category,
    }
    params = {k: v for k, v in params.items() if v is not None}
    params["query_embedding"] = query_vector

    result = supabase.rpc("match_recipes", params).execute()
    return result.data


def query_meal(
    main_query: str,
    side_query: str = None,
    mains_count: int = 3,
    sides_count: int = 3,
    min_calories: float = None,
    max_calories: float = None,
    min_protein: float = None,
    max_protein: float = None,
):
    """Dual-query for balanced meal: separate searches for mains and sides."""
    if side_query is None:
        side_query = main_query

    macro_kwargs = {
        "min_calories": min_calories,
        "max_calories": max_calories,
        "min_protein": min_protein,
        "max_protein": max_protein,
    }

    mains = query_recipes(main_query, match_count=mains_count, filter_category="main-dish", **macro_kwargs)
    sides = query_recipes(side_query, match_count=sides_count, filter_category="side-dish", **macro_kwargs)

    return {"mains": mains, "sides": sides}


def format_recipes_as_context(recipes: list[dict]) -> str:
    if not recipes:
        return "No recipes found."
    lines = []
    for i, r in enumerate(recipes, 1):
        line = f"{i}. {r['title']}"
        if r.get("category"):
            line += f" [{r['category']}]"
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
        if r.get("description"):
            line += f"\n   {r['description'][:120]}"
        lines.append(line)
    return "\n".join(lines)


def format_meal_as_context(meal: dict) -> str:
    mains_text = format_recipes_as_context(meal.get("mains", []))
    sides_text = format_recipes_as_context(meal.get("sides", []))
    return f"MAIN DISHES:\n{mains_text}\n\nSIDE DISHES:\n{sides_text}"


def generate_response(user_query: str, recipes: list[dict]) -> str:
    _, _, claude = _get_clients()
    context = format_recipes_as_context(recipes)
    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=(
            "You are a helpful nutrition and meal planning assistant. "
            "You have access to a database of recipes with macro information. "
            "Answer the user's question using only the retrieved recipes provided. "
            "Be concise and practical."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"User query: {user_query}\n\n"
                    f"Retrieved recipes:\n{context}\n\n"
                    "Based on these recipes, answer the user's query."
                ),
            }
        ],
    )
    return response.content[0].text


def generate_meal_response(user_query: str, meal: dict) -> str:
    _, _, claude = _get_clients()
    context = format_meal_as_context(meal)
    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=(
            "You are a helpful meal planning assistant. "
            "You suggest balanced meals by pairing main dishes with complementary sides. "
            "Use only the retrieved recipes provided. "
            "Suggest 1-2 complete meal combinations, explaining why they pair well. "
            "Include combined macro totals where possible. Be concise."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"User query: {user_query}\n\n"
                    f"Retrieved recipes:\n{context}\n\n"
                    "Suggest a balanced meal pairing from these options."
                ),
            }
        ],
    )
    return response.content[0].text


def main():
    print("=== Single recipe query ===")
    query = "Healthy dinner recipes with no oven baking involved"
    recipes = query_recipes(query, min_protein=20, max_calories=600, match_count=5)
    print(f"Retrieved {len(recipes)} recipes\n")
    answer = generate_response(query, recipes)
    print(answer)

    print("\n=== Meal pairing query ===")
    meal_query = "healthy Asian-style dinner"
    meal = query_meal(
        main_query=meal_query,
        side_query="light vegetable side dish",
        mains_count=3,
        sides_count=3,
    )
    print(f"Mains: {len(meal['mains'])}, Sides: {len(meal['sides'])}\n")
    meal_answer = generate_meal_response(meal_query, meal)
    print(meal_answer)


if __name__ == "__main__":
    main()
