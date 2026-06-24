import json
import os
import anthropic
from utils import get_supabase_client
from query_recipes import query_recipes
from workout_calories import is_cardio

_MEAL_SLOTS = ["breakfast", "lunch", "dinner", "snack"]

_claude = None


def _get_claude():
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _claude


def _compute_remaining(target: dict, workout_burn: float, food_logged: list[dict], cardio_burn: float = 0.0) -> dict:
    # Only cardio burn (≥50% if >300 kcal) adds to calorie budget; weights burn stays as deficit
    cardio_add = (cardio_burn * 0.5) if cardio_burn > 300 else cardio_burn
    total_calories = target["base_calories"] + cardio_add
    consumed_calories = sum(f["calories"] for f in food_logged)
    consumed_protein = sum(f["protein_g"] for f in food_logged)
    consumed_carbs = sum(f["carbs_g"] for f in food_logged)
    consumed_fat = sum(f["fat_g"] for f in food_logged)
    logged_slots = {f["meal_slot"] for f in food_logged}
    return {
        "remaining_calories": round(total_calories - consumed_calories, 1),
        "remaining_protein_g": round(target["goal_protein_g"] - consumed_protein, 1),
        "remaining_carbs_g": round(target["goal_carbs_g"] - consumed_carbs, 1),
        "remaining_fat_g": round(target["goal_fat_g"] - consumed_fat, 1),
        "slots_needed": [s for s in _MEAL_SLOTS if s not in logged_slots],
    }


def get_daily_budget(user_id: str, date: str) -> dict:
    supabase = get_supabase_client()

    target_row = (
        supabase.table("daily_targets")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", date)
        .single()
        .execute()
    )
    target = target_row.data

    workout_rows = (
        supabase.table("workout_logs")
        .select("exercise_type, calories_burned")
        .eq("user_id", user_id)
        .eq("date", date)
        .execute()
    )
    workout_burn = sum(r["calories_burned"] for r in workout_rows.data)
    cardio_burn = sum(r["calories_burned"] for r in workout_rows.data if is_cardio(r["exercise_type"]))

    food_rows = (
        supabase.table("food_logs")
        .select("meal_slot, calories, protein_g, carbs_g, fat_g")
        .eq("user_id", user_id)
        .eq("date", date)
        .execute()
    )

    remaining = _compute_remaining(target, workout_burn, food_rows.data, cardio_burn=cardio_burn)
    return {
        "target": target,
        "workout_burn": workout_burn,
        "cardio_burn": cardio_burn,
        "remaining": remaining,
    }


def build_daily_plan(user_id: str, date: str, preferences: list[str] = None) -> dict:
    budget = get_daily_budget(user_id, date)
    remaining = budget["remaining"]
    slots_needed = remaining["slots_needed"]

    if not slots_needed:
        return {"message": "All meals logged for today.", "plan": [], "budget": budget}

    n_slots = len(slots_needed)
    per_slot_cal = max(100, remaining["remaining_calories"] / n_slots)
    per_slot_protein = max(0, remaining["remaining_protein_g"] / n_slots)

    pref_str = ", ".join(preferences or []) or "none"
    slot_labels = {
        "breakfast": "healthy breakfast",
        "lunch": "lunch",
        "dinner": "dinner",
        "snack": "light snack",
    }

    # Snack slot: skip RAG (cookbook recipes are full dishes, not snacks)
    # Claude will suggest real snacks from nutrition knowledge instead
    SNACK_BYPASS = True

    candidates_by_slot = {}
    for slot in slots_needed:
        if slot == "snack" and SNACK_BYPASS:
            candidates_by_slot[slot] = []
            continue
        label = slot_labels.get(slot, slot)
        query = f"{label} {pref_str} around {int(per_slot_cal)} calories {int(per_slot_protein)}g protein"
        results = query_recipes(
            query,
            match_count=5,
            max_calories=per_slot_cal * 1.4,
            min_protein=max(0, per_slot_protein * 0.5),
        )
        candidates_by_slot[slot] = results

    slots_text = ""
    for slot, recipes in candidates_by_slot.items():
        slots_text += f"\n## {slot.upper()} candidates\n"
        if not recipes:
            slots_text += "NO CANDIDATES — use your nutrition knowledge for a quick no-cook snack.\n"
        for r in recipes:
            slots_text += (
                f"- [{r['id']}] {r['title']}: "
                f"{r.get('calories') or '?'} kcal, "
                f"{r.get('protein_g') or '?'}g protein, "
                f"{r.get('carbohydrate_g') or '?'}g carbs, "
                f"{r.get('fat_g') or '?'}g fat\n"
            )

    prompt = f"""You are a sports nutritionist coaching someone who lifts weights and does cardio. Apply these evidence-based rules when building the meal plan:

NUTRITION RULES:
- Goal is body recomposition (cut fat, build/maintain strength). Maintain a 250-500 kcal daily deficit.
- Do NOT recommend eating back calories burned from weight training (legs, push, pull, weights, strength, crossfit). Those calories stay as deficit.
- For cardio (run, jog, cycling, swim, rowing, elliptical): eat back ~50% of calories burned only if burn > 400 kcal.
- Protein target: 2.3-3.1g per kg bodyweight (65kg user = 150-200g/day). Prioritise hitting protein above all other macros.
- On training days: favour higher carbs to fuel performance and glycogen replenishment.
- On rest days: lower carbs, higher fat, same protein.
- Post strength-workout: surface a high-protein snack (25-40g protein + fast carbs) as the immediate next suggestion. This is the anabolic window.
- Distribute protein across 3-5 meals (~0.4g/kg per meal = ~26g per meal for this user).
- Never sacrifice protein to hit calorie target — it is better to be slightly over calories than under on protein.

Build a meal plan to hit the user's remaining macro targets for today.

REMAINING TARGETS:
- Calories: {remaining['remaining_calories']:.0f} kcal
- Protein: {remaining['remaining_protein_g']:.0f}g
- Carbs: {remaining['remaining_carbs_g']:.0f}g
- Fat: {remaining['remaining_fat_g']:.0f}g

SLOTS NEEDED: {', '.join(slots_needed)}
PREFERENCES: {pref_str}

RECIPE CANDIDATES (pick one per slot, from the recipe database):
{slots_text}
For slots marked "NO CANDIDATES" (e.g. snack): use your own nutrition knowledge to suggest a real snack — something quick and no-cook like Greek yoghurt, cottage cheese, protein shake, boiled eggs, rice cakes with nut butter, fruit + nuts. Set recipe_id to null for these.

Pick the best option per slot so the combination hits the targets. Prioritise protein.

Respond ONLY with valid JSON:
{{
  "plan": [
    {{
      "slot": "lunch",
      "recipe_id": "...",
      "recipe_name": "...",
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "reason": "one sentence"
    }}
  ],
  "total_planned": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}},
  "protein_gap": 0,
  "protein_warning": null,
  "coach_note": "one sentence summary"
}}

Rules for protein_gap and protein_warning:
- protein_gap = remaining_protein_target - total_planned.protein_g (0 if on target)
- protein_warning = null if gap <= 10g, otherwise a short actionable fix e.g. "Add a protein shake (+25g) or 200g cottage cheese (+24g) to close the gap."""

    response = _get_claude().messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    plan = json.loads(raw)

    return {"budget": budget, **plan}
