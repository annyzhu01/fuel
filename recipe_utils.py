"""Shared recipe formatting and meal-planning helpers used across the codebase."""

import json
import re

MEAL_SLOTS = ["breakfast", "lunch", "dinner", "snack"]

SLOT_LABELS = {
    "breakfast": "healthy breakfast",
    "lunch": "lunch",
    "dinner": "dinner",
    "snack": "light snack",
}


def format_recipe_candidate(recipe: dict) -> str:
    """Format a single recipe dict into a one-line summary string."""
    return (
        f"- [{recipe['id']}] {recipe['title']}: "
        f"{recipe.get('calories') or '?'} kcal, "
        f"{recipe.get('protein_g') or '?'}g protein, "
        f"{recipe.get('carbohydrate_g') or '?'}g carbs, "
        f"{recipe.get('fat_g') or '?'}g fat"
    )


def format_recipe_candidates(recipes: list[dict]) -> str:
    """Format a list of recipe dicts into a newline-separated summary."""
    if not recipes:
        return "NO CANDIDATES — use your nutrition knowledge for a quick no-cook snack."
    return "\n".join(format_recipe_candidate(r) for r in recipes)


def compute_per_slot_budget(remaining: dict) -> tuple[float, float]:
    """Compute per-slot calorie and protein budgets from remaining macro targets.

    Returns (per_slot_calories, per_slot_protein).
    """
    n_slots = max(1, len(remaining.get("slots_needed", [])) or 1)
    per_slot_cal = max(100, remaining["remaining_calories"] / n_slots)
    per_slot_protein = max(0, remaining["remaining_protein_g"] / n_slots)
    return per_slot_cal, per_slot_protein


def parse_json_response(text: str) -> list | dict:
    """Parse a JSON response from an LLM, stripping markdown fences if present."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown code fences
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try regex extraction
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("Could not parse JSON from LLM response", text, 0)


def get_ingredient_names(supabase, recipe_id: str) -> list[str]:
    """Fetch ingredient names for a recipe from the recipe_ingredients join table."""
    result = (
        supabase.table("recipe_ingredients")
        .select("ingredients(name)")
        .eq("recipe_id", recipe_id)
        .execute()
    )
    return [row["ingredients"]["name"] for row in result.data if row.get("ingredients")]
