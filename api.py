import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from workout_calories import estimate_calories_burned
from daily_plan import get_daily_budget, build_daily_plan
from utils import get_supabase_client


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
DEFAULT_USER_WEIGHT_KG = 70.0
BASE_CALORIES = 1800
GOAL_PROTEIN_G = 120
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


@app.get("/daily-plan")
def daily_plan(preferences: str = ""):
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    return build_daily_plan(USER_ID, str(date.today()), prefs)
