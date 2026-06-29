from utils import get_anthropic_client
from daily_plan import get_daily_budget
from pantry import get_pantry
from query_recipes import query_recipes
from recipe_utils import format_recipe_candidate

MAX_SEARCH_CALLS = 3


_TOOLS = [
    {
        "name": "search_recipes",
        "description": (
            "Search the recipe database by natural language query with optional macro filters. "
            "Prefer recipes that use the user's pantry ingredients. "
            "For the snack slot: do NOT call this tool — call submit_plan directly with a no-cook snack."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language e.g. 'high protein chicken lunch'"},
                "slot": {"type": "string", "description": "Which meal slot: breakfast, lunch, dinner"},
                "max_calories": {"type": "number"},
                "min_protein": {"type": "number"},
            },
            "required": ["query", "slot"],
        },
    },
    {
        "name": "submit_plan",
        "description": "Submit the final meal plan. Call when all slots are filled or search budget is exhausted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "slot": {"type": "string"},
                            "recipe_id": {"type": ["string", "null"]},
                            "recipe_name": {"type": "string"},
                            "calories": {"type": "number"},
                            "protein_g": {"type": "number"},
                            "carbs_g": {"type": "number"},
                            "fat_g": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["slot", "recipe_name", "calories", "protein_g", "carbs_g", "fat_g", "reason"],
                    },
                },
                "total_planned": {
                    "type": "object",
                    "properties": {
                        "calories": {"type": "number"},
                        "protein_g": {"type": "number"},
                        "carbs_g": {"type": "number"},
                        "fat_g": {"type": "number"},
                    },
                },
                "protein_gap": {"type": "number", "description": "How many grams of protein short of target. 0 if on target."},
                "protein_warning": {"type": ["string", "null"], "description": "Actionable fix if protein_gap > 10g, else null."},
                "coach_note": {"type": "string"},
            },
            "required": ["plan", "total_planned", "protein_gap", "coach_note"],
        },
    },
]


def _build_system_prompt(remaining: dict, pantry: list, preferences: list) -> str:
    pantry_str = ", ".join(pantry) if pantry else "nothing specified"
    pref_str = ", ".join(preferences) if preferences else "none"
    slots = ", ".join(remaining["slots_needed"])

    return f"""You are a sports nutritionist building a meal plan for someone doing body recomposition (cut + strength, 65kg).

NUTRITION RULES:
- Protein is priority #1. Target: 150-200g/day. Never sacrifice protein for calories.
- Do NOT eat back calories from weight training. Cardio: eat back 50% only if burn > 300 kcal.
- Distribute protein: ~26g minimum per meal.
- Training days: favour higher carbs. Rest days: lower carbs, higher fat.
- Snack slot: use your own knowledge — quick no-cook options only (Greek yoghurt, cottage cheese, boiled eggs, protein shake, rice cakes + nut butter). Set recipe_id to null.

USER CONTEXT:
- Pantry (ingredients at home): {pantry_str}. PREFER recipes using these ingredients.
- Preferences: {pref_str}

REMAINING MACRO TARGETS FOR TODAY:
- Calories: {remaining['remaining_calories']:.0f} kcal
- Protein: {remaining['remaining_protein_g']:.0f}g
- Carbs: {remaining['remaining_carbs_g']:.0f}g
- Fat: {remaining['remaining_fat_g']:.0f}g

SLOTS NEEDED: {slots}
SEARCH BUDGET: {MAX_SEARCH_CALLS} search_recipes calls total across all slots. Use them wisely.

STRATEGY:
1. Search for each non-snack slot. Prefer pantry ingredients in your query.
2. If results are unsatisfying (protein too low, calories over budget), refine and search again — but remember your search budget.
3. For snack: call submit_plan directly with a no-cook suggestion from your knowledge.
4. Call submit_plan when all slots are filled or budget is exhausted.
5. protein_gap = target_protein - total_planned_protein (0 if on target or over).
6. protein_warning = null if gap <= 10g, otherwise a short actionable tip.

IMPORTANT: Every recipe must be unique — NEVER assign the same recipe to more than one slot. Each slot must have a different recipe_id."""


def build_daily_plan_agentic(user_id: str, date: str, preferences: list = None) -> dict:
    budget = get_daily_budget(user_id, date)
    remaining = budget["remaining"]

    if not remaining["slots_needed"]:
        return {"message": "All meals logged for today.", "plan": [], "budget": budget}

    pantry = get_pantry(user_id)
    system_prompt = _build_system_prompt(remaining, pantry, preferences or [])

    messages = [{"role": "user", "content": "Build the meal plan now."}]
    search_count = 0
    turn_count = 0
    end_turn_nudges = 0
    seen_ids: set[str] = set()
    claude = get_anthropic_client()

    while True:
        turn_count += 1
        if turn_count > MAX_SEARCH_CALLS * 3:
            raise RuntimeError("Agentic planner exceeded max turns")
        response = claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            system=system_prompt,
            tools=_TOOLS,
            messages=messages,
        )

        # Append assistant response to message history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Claude stopped without calling submit_plan — force it
            end_turn_nudges += 1
            if end_turn_nudges >= 2:
                raise RuntimeError("Claude did not call submit_plan after nudging")
            messages.append({
                "role": "user",
                "content": "You MUST call submit_plan now. Do not respond with text only.",
            })
            continue

        # Process tool calls
        tool_results = []
        should_submit = False

        for block in response.content:
            if block.type != "tool_use":
                continue

            # Reset nudge counter when a tool_use block is processed
            end_turn_nudges = 0

            if block.name == "search_recipes":
                search_count += 1
                kwargs = dict(block.input)
                kwargs.pop("slot", None)
                query_text = kwargs.pop("query")
                results = query_recipes(
                    semantic_query=query_text,
                    match_count=5,
                    max_calories=kwargs.get("max_calories"),
                    min_protein=kwargs.get("min_protein"),
                )
                # Exclude recipes already shown for other slots
                results = [r for r in results if r.get("id") not in seen_ids]
                for r in results:
                    if r.get("id"):
                        seen_ids.add(r["id"])

                result_text = f"Results for '{query_text}' ({block.input.get('slot', '')}):\n"
                if not results:
                    result_text += "No results found."
                else:
                    for r in results:
                        result_text += format_recipe_candidate(r) + "\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

                if search_count >= MAX_SEARCH_CALLS:
                    should_submit = True

            elif block.name == "submit_plan":
                plan = block.input
                # Deduplicate: drop later occurrences of the same recipe_id
                if "plan" in plan:
                    used: set[str] = set()
                    deduped = []
                    for item in plan["plan"]:
                        rid = item.get("recipe_id")
                        if rid and rid in used:
                            item = {**item, "recipe_id": None,
                                    "reason": "Swapped to avoid duplicate (no DB alternative)"}
                        elif rid:
                            used.add(rid)
                        deduped.append(item)
                    plan["plan"] = deduped
                return {"budget": budget, **plan}

        if should_submit:
            tool_results.append({
                "type": "text",
                "text": f"Search budget exhausted ({MAX_SEARCH_CALLS}/{MAX_SEARCH_CALLS}). You MUST call submit_plan now with whatever plan you have.",
            })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
