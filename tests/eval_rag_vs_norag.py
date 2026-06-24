"""
Compare meal suggestions: RAG-grounded vs Claude-only (no retrieval).
Run: python -m tests.eval_rag_vs_norag
"""
import json
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

REMAINING = {
    "remaining_calories": 1200,
    "remaining_protein_g": 110,
    "remaining_carbs_g": 130,
    "remaining_fat_g": 35,
    "slots_needed": ["lunch", "dinner", "snack"],
}

NUTRITION_RULES = """You are a sports nutritionist coaching someone who lifts weights (cut + strength goal, 65kg).
- Protein priority: 150-200g/day total. Never sacrifice protein for calories.
- Distribute protein: ~26g per meal minimum.
- Snack = quick no-cook food (Greek yoghurt, eggs, cottage cheese, protein shake, rice cakes). NOT a cooked dish.
- Favour high protein, moderate carbs, lower fat."""


def _claude():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def run_norag(remaining: dict) -> dict:
    """Claude suggests meals with zero recipe context."""
    prompt = f"""{NUTRITION_RULES}

Suggest one meal per slot to hit these remaining targets:
- Calories: {remaining['remaining_calories']} kcal
- Protein: {remaining['remaining_protein_g']}g
- Carbs: {remaining['remaining_carbs_g']}g
- Fat: {remaining['remaining_fat_g']}g

Slots: {', '.join(remaining['slots_needed'])}

Respond ONLY valid JSON:
{{
  "plan": [
    {{
      "slot": "lunch",
      "recipe_name": "...",
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "reason": "one sentence"
    }}
  ],
  "total_planned": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}},
  "coach_note": "one sentence"
}}"""

    response = _claude().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def run_rag(remaining: dict) -> dict:
    """RAG-grounded: retrieve candidates then Claude picks."""
    from query_recipes import query_recipes

    n_slots = len(remaining["slots_needed"])
    per_slot_cal = remaining["remaining_calories"] / n_slots
    per_slot_protein = remaining["remaining_protein_g"] / n_slots

    slot_labels = {"breakfast": "healthy breakfast", "lunch": "lunch", "dinner": "dinner", "snack": "light snack"}

    candidates_by_slot = {}
    for slot in remaining["slots_needed"]:
        if slot == "snack":
            candidates_by_slot[slot] = []
            continue
        label = slot_labels.get(slot, slot)
        query = f"{label} around {int(per_slot_cal)} calories {int(per_slot_protein)}g protein"
        candidates_by_slot[slot] = query_recipes(query, match_count=5, max_calories=per_slot_cal * 1.4)

    slots_text = ""
    for slot, recipes in candidates_by_slot.items():
        slots_text += f"\n## {slot.upper()}\n"
        if not recipes:
            slots_text += "NO CANDIDATES — use your knowledge for a quick no-cook snack.\n"
        for r in recipes:
            slots_text += f"- [{r['id']}] {r['title']}: {r.get('calories') or '?'} kcal, {r.get('protein_g') or '?'}g protein\n"

    prompt = f"""{NUTRITION_RULES}

Pick one meal per slot from these recipe candidates to hit remaining targets:
- Calories: {remaining['remaining_calories']} kcal
- Protein: {remaining['remaining_protein_g']}g
- Carbs: {remaining['remaining_carbs_g']}g
- Fat: {remaining['remaining_fat_g']}g

{slots_text}

Respond ONLY valid JSON:
{{
  "plan": [
    {{
      "slot": "lunch",
      "recipe_name": "...",
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "reason": "one sentence"
    }}
  ],
  "total_planned": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}},
  "coach_note": "one sentence"
}}"""

    response = _claude().messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def score(plan: dict, remaining: dict) -> dict:
    total = plan.get("total_planned", {})
    cal_err = abs(total.get("calories", 0) - remaining["remaining_calories"])
    protein_err = abs(total.get("protein_g", 0) - remaining["remaining_protein_g"])
    return {
        "calorie_error": round(cal_err, 1),
        "protein_error": round(protein_err, 1),
        "hit_protein": total.get("protein_g", 0) >= remaining["remaining_protein_g"] * 0.85,
    }


def print_plan(label: str, plan: dict, remaining: dict):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    for item in plan.get("plan", []):
        print(f"  [{item['slot']}] {item['recipe_name']}")
        print(f"         {item['calories']} kcal | {item['protein_g']}g protein | {item['carbs_g']}g carbs | {item['fat_g']}g fat")
        print(f"         → {item['reason']}")
    t = plan.get("total_planned", {})
    print(f"\n  TOTALS: {t.get('calories')} kcal | {t.get('protein_g')}g protein")
    print(f"  TARGET: {remaining['remaining_calories']} kcal | {remaining['remaining_protein_g']}g protein")
    s = score(plan, remaining)
    print(f"  SCORE:  cal_error={s['calorie_error']} | protein_error={s['protein_error']} | hit_protein={s['hit_protein']}")
    print(f"\n  Coach: {plan.get('coach_note', '')}")


if __name__ == "__main__":
    print("Running RAG vs No-RAG comparison...")
    print(f"Remaining budget: {REMAINING['remaining_calories']} kcal | {REMAINING['remaining_protein_g']}g protein")
    print(f"Slots: {REMAINING['slots_needed']}")

    norag = run_norag(REMAINING)
    print_plan("NO-RAG (Claude only)", norag, REMAINING)

    rag = run_rag(REMAINING)
    print_plan("RAG (recipe database)", rag, REMAINING)

    print("\n\n=== COMPARISON ===")
    ns = score(norag, REMAINING)
    rs = score(rag, REMAINING)
    winner_cal = "RAG" if rs["calorie_error"] < ns["calorie_error"] else "No-RAG"
    winner_protein = "RAG" if rs["protein_error"] < ns["protein_error"] else "No-RAG"
    print(f"  Calorie accuracy: {winner_cal} wins (RAG err={rs['calorie_error']}, No-RAG err={ns['calorie_error']})")
    print(f"  Protein accuracy: {winner_protein} wins (RAG err={rs['protein_error']}, No-RAG err={ns['protein_error']})")
    print(f"  RAG hit protein target: {rs['hit_protein']}")
    print(f"  No-RAG hit protein target: {ns['hit_protein']}")
