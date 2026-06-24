const BASE = "http://localhost:8000";

export interface Remaining {
  remaining_calories: number;
  remaining_protein_g: number;
  remaining_carbs_g: number;
  remaining_fat_g: number;
  slots_needed: string[];
}

export interface Budget {
  target: {
    base_calories: number;
    goal_protein_g: number;
    goal_carbs_g: number;
    goal_fat_g: number;
  };
  workout_burn: number;
  remaining: Remaining;
}

export interface PlanItem {
  slot: string;
  recipe_id: string;
  recipe_name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  reason: string;
}

export interface DailyPlan {
  budget: Budget;
  plan: PlanItem[];
  total_planned: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
  protein_gap: number;
  protein_warning: string | null;
  coach_note: string;
}

export async function getBudget(): Promise<Budget> {
  const res = await fetch(`${BASE}/budget`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch budget");
  return res.json();
}

export async function getDailyPlan(): Promise<DailyPlan> {
  const res = await fetch(`${BASE}/daily-plan`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch plan");
  return res.json();
}

export async function logWorkout(exercise_type: string, duration_minutes: number) {
  const res = await fetch(`${BASE}/log-workout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exercise_type, duration_minutes }),
  });
  if (!res.ok) throw new Error("Failed to log workout");
  return res.json();
}

export async function logMeal(payload: {
  meal_slot: string;
  description: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}) {
  const res = await fetch(`${BASE}/log-meal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to log meal");
  return res.json();
}

export interface RecipeDetail {
  id: string;
  title: string;
  description: string | null;
  steps: string[];
  calories: number;
  protein_g: number;
  carbohydrate_g: number;
  fat_g: number;
  prep_time: string | null;
  cook_time: string | null;
  servings: string | null;
  category: string | null;
}

export async function getRecipe(id: string): Promise<RecipeDetail> {
  const res = await fetch(`${BASE}/recipe/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch recipe");
  return res.json();
}

export async function swapMeal(slot: string, excludeId: string): Promise<PlanItem> {
  const res = await fetch(`${BASE}/swap-meal?slot=${slot}&exclude_id=${encodeURIComponent(excludeId)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to swap meal");
  return res.json();
}

export async function getPantry(): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch pantry");
  const data = await res.json();
  return data.items;
}

export async function addToPantry(ingredient: string): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredient }),
  });
  if (!res.ok) throw new Error("Failed to add to pantry");
  const data = await res.json();
  return data.items;
}

export async function removeFromPantry(ingredient: string): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry/${encodeURIComponent(ingredient)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to remove from pantry");
  const data = await res.json();
  return data.items;
}
