import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from workout_calories import estimate_calories_burned
from query_recipes import query_recipes
from daily_plan import get_daily_budget, build_daily_plan
from daily_plan_agentic import build_daily_plan_agentic
from utils import get_supabase_client, get_anthropic_client
from pantry import get_pantry, add_to_pantry, remove_from_pantry
from recipe_utils import SLOT_LABELS, compute_per_slot_budget, get_ingredient_names


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_today_target()
    yield


app = FastAPI(title="Fuel API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_ID = "mvp-user"
DEFAULT_USER_WEIGHT_KG = 65.0
BASE_CALORIES = 1800
GOAL_PROTEIN_G = 160
GOAL_CARBS_G = 200
GOAL_FAT_G = 60


def _ensure_today_target():
    """Upsert today's daily target so the app works without manual seeding."""
    supabase = get_supabase_client()
    today = str(date.today())
    supabase.table("daily_targets").upsert(
        {
            "user_id": USER_ID,
            "date": today,
            "base_calories": BASE_CALORIES,
            "goal_protein_g": GOAL_PROTEIN_G,
            "goal_carbs_g": GOAL_CARBS_G,
            "goal_fat_g": GOAL_FAT_G,
        },
        on_conflict="user_id,date",
    ).execute()



class WorkoutLog(BaseModel):
    exercise_type: str
    duration_minutes: float


class MealLog(BaseModel):
    meal_slot: str
    description: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/budget")
def budget(target_date: str = None):
    d = target_date or str(date.today())
    return get_daily_budget(USER_ID, d)


@app.post("/log-workout")
def log_workout(body: WorkoutLog):
    calories_burned = estimate_calories_burned(
        body.exercise_type, body.duration_minutes, DEFAULT_USER_WEIGHT_KG
    )
    supabase = get_supabase_client()
    supabase.table("workout_logs").insert({
        "user_id": USER_ID,
        "date": str(date.today()),
        "exercise_type": body.exercise_type,
        "duration_minutes": body.duration_minutes,
        "calories_burned": calories_burned,
    }).execute()
    updated = get_daily_budget(USER_ID, str(date.today()))
    return {"calories_burned": calories_burned, "updated_budget": updated}


@app.post("/log-meal")
def log_meal(body: MealLog):
    if body.meal_slot not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(400, "meal_slot must be breakfast, lunch, dinner, or snack")
    supabase = get_supabase_client()
    supabase.table("food_logs").insert({
        "user_id": USER_ID,
        "date": str(date.today()),
        "meal_slot": body.meal_slot,
        "description": body.description,
        "calories": body.calories,
        "protein_g": body.protein_g,
        "carbs_g": body.carbs_g,
        "fat_g": body.fat_g,
    }).execute()
    updated = get_daily_budget(USER_ID, str(date.today()))
    return {"logged": True, "updated_budget": updated}


@app.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: str):
    import httpx
    for attempt in range(3):
        try:
            supabase = get_supabase_client()
            row = (
                supabase.table("recipes")
                .select("id, title, description, steps, calories, protein_g, carbohydrate_g, fat_g, prep_time, cook_time, servings, category, healthy_tip")
                .eq("id", recipe_id)
                .single()
                .execute()
            )
            if not row.data:
                raise HTTPException(404, "Recipe not found")
            recipe = row.data
            break
        except httpx.ReadError:
            if attempt == 2:
                raise HTTPException(503, "Database connection error, please retry")
    recipe["ingredients"] = get_ingredient_names(supabase, recipe_id)

    if not recipe.get("healthy_tip"):
        client = get_anthropic_client()
        ing_list = ", ".join(recipe["ingredients"][:15]) or "unknown"
        tip_resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=120,
            messages=[{
                "role": "user",
                "content": (
                    f"Recipe: {recipe['title']}\n"
                    f"Macros: {recipe.get('calories', '?')} kcal, {recipe.get('protein_g', '?')}g protein, "
                    f"{recipe.get('carbohydrate_g', '?')}g carbs, {recipe.get('fat_g', '?')}g fat\n"
                    f"Ingredients: {ing_list}\n\n"
                    "Give ONE concise healthy tip (2-3 sentences max): suggest a specific vegetable to add to bulk it up, "
                    "or one swap to reduce calories while preserving taste. Be specific and practical. No intro phrases."
                ),
            }],
        )
        tip = tip_resp.content[0].text.strip()
        supabase.table("recipes").update({"healthy_tip": tip}).eq("id", recipe_id).execute()
        recipe["healthy_tip"] = tip

    return recipe


@app.get("/swap-meal")
def swap_meal(slot: str, exclude_ids: str = "", vibe: str = ""):
    if slot not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(400, "slot must be breakfast, lunch, dinner, or snack")
    excluded = set(i.strip() for i in exclude_ids.split(",") if i.strip())
    budget = get_daily_budget(USER_ID, str(date.today()))
    remaining = budget["remaining"]
    per_slot_cal, per_slot_protein = compute_per_slot_budget(remaining)
    label = SLOT_LABELS[slot]
    vibe_str = f" {vibe.strip()}" if vibe.strip() else ""
    results = query_recipes(
        f"{label}{vibe_str} around {int(per_slot_cal)} calories {int(per_slot_protein)}g protein",
        match_count=50,
        max_calories=per_slot_cal * 1.4,
        min_protein=max(0, per_slot_protein * 0.5),
    )
    import random
    results = [r for r in results if r.get("id") not in excluded]
    if not results:
        raise HTTPException(404, "No alternative recipe found")
    r = random.choice(results[:10])
    return {
        "slot": slot,
        "recipe_id": r.get("id"),
        "recipe_name": r.get("title"),
        "calories": r.get("calories") or 0,
        "protein_g": r.get("protein_g") or 0,
        "carbs_g": r.get("carbohydrate_g") or 0,
        "fat_g": r.get("fat_g") or 0,
        "reason": "Alternative suggestion",
    }


@app.get("/daily-plan")
def daily_plan(preferences: str = "", agentic: bool = False):
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    if agentic:
        return build_daily_plan_agentic(USER_ID, str(date.today()), prefs)
    return build_daily_plan(USER_ID, str(date.today()), prefs)


class PantryAdd(BaseModel):
    ingredient: str


@app.get("/pantry")
def pantry_get():
    return {"items": get_pantry(USER_ID)}


@app.post("/pantry")
def pantry_add(body: PantryAdd):
    if not body.ingredient.strip():
        raise HTTPException(400, "ingredient must not be empty")
    items = add_to_pantry(USER_ID, body.ingredient)
    return {"added": body.ingredient.strip().lower(), "items": items}


@app.delete("/pantry/{ingredient}")
def pantry_remove(ingredient: str):
    items = remove_from_pantry(USER_ID, ingredient)
    return {"removed": ingredient.lower(), "items": items}
