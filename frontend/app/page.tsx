"use client";

import { useEffect, useState } from "react";
import {
  getBudget,
  getDailyPlan,
  logWorkout,
  logMeal,
  Budget,
  DailyPlan,
  PlanItem,
} from "@/lib/api";
import { MacroRing } from "@/components/MacroRing";
import { MealCard } from "@/components/MealCard";

export default function TodayPage() {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showWorkout, setShowWorkout] = useState(false);
  const [exercise, setExercise] = useState("");
  const [duration, setDuration] = useState("");
  const [logging, setLogging] = useState(false);

  async function refresh() {
    const b = await getBudget();
    setBudget(b);
  }

  async function refreshPlan() {
    setPlanLoading(true);
    try {
      const p = await getDailyPlan();
      setPlan(p);
    } catch (e) {
      console.error("Plan fetch failed", e);
    } finally {
      setPlanLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        await refresh();
        await refreshPlan();
      } catch {
        setError("Cannot reach API. Is the backend running on port 8000?");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  async function handleLogWorkout() {
    if (!exercise || !duration) return;
    setLogging(true);
    try {
      await logWorkout(exercise, parseFloat(duration));
      setShowWorkout(false);
      setExercise("");
      setDuration("");
      await refresh();
      await refreshPlan();
    } finally {
      setLogging(false);
    }
  }

  async function handleLogMeal(item: PlanItem) {
    await logMeal({
      meal_slot: item.slot,
      description: item.recipe_name,
      calories: item.calories,
      protein_g: item.protein_g,
      carbs_g: item.carbs_g,
      fat_g: item.fat_g,
    });
    await refresh();
    await refreshPlan();
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-400 text-sm px-8 text-center">
        {error}
      </div>
    );
  }

  const r = budget?.remaining;
  const t = budget?.target;
  const totalCal = (t?.base_calories ?? 0) + (budget?.workout_burn ?? 0);

  return (
    <main className="min-h-screen max-w-md mx-auto p-4 flex flex-col gap-6">
      <div className="flex justify-between items-center pt-4">
        <h1 className="text-2xl font-bold text-white">Fuel</h1>
        {(budget?.workout_burn ?? 0) > 0 && (
          <span className="text-green-400 text-sm font-medium">
            +{budget!.workout_burn} kcal burned
          </span>
        )}
      </div>

      {r && t && (
        <div className="flex justify-around bg-gray-900 rounded-2xl p-4">
          <MacroRing remaining={r.remaining_calories} total={totalCal} label="kcal" color="#22c55e" />
          <MacroRing remaining={r.remaining_protein_g} total={t.goal_protein_g} label="protein" color="#3b82f6" />
          <MacroRing remaining={r.remaining_carbs_g} total={t.goal_carbs_g} label="carbs" color="#f59e0b" />
          <MacroRing remaining={r.remaining_fat_g} total={t.goal_fat_g} label="fat" color="#ef4444" />
        </div>
      )}

      <button
        onClick={() => setShowWorkout(!showWorkout)}
        className="w-full bg-gray-800 hover:bg-gray-700 text-white rounded-xl py-3 font-semibold transition-colors"
      >
        {showWorkout ? "Cancel" : "+ Log Workout"}
      </button>

      {showWorkout && (
        <div className="bg-gray-800 rounded-xl p-4 flex flex-col gap-3">
          <input
            className="bg-gray-700 text-white rounded-lg px-3 py-2 text-sm placeholder-gray-400 outline-none focus:ring-1 focus:ring-green-500"
            placeholder="Exercise type (e.g. run, weights, legs)"
            value={exercise}
            onChange={(e) => setExercise(e.target.value)}
          />
          <input
            className="bg-gray-700 text-white rounded-lg px-3 py-2 text-sm placeholder-gray-400 outline-none focus:ring-1 focus:ring-green-500"
            placeholder="Duration (minutes)"
            type="number"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
          <button
            onClick={handleLogWorkout}
            disabled={logging || !exercise || !duration}
            className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg py-2 font-semibold text-sm transition-colors"
          >
            {logging ? "Saving..." : "Save Workout"}
          </button>
        </div>
      )}

      {plan?.coach_note && (
        <p className="text-gray-400 text-sm italic px-1">{plan.coach_note}</p>
      )}

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-white">What to eat</h2>
        {planLoading ? (
          <p className="text-gray-400 text-sm">Updating suggestions...</p>
        ) : plan?.plan?.length ? (
          plan.plan.map((item, i) => (
            <MealCard key={i} item={item} onLog={handleLogMeal} />
          ))
        ) : (
          <p className="text-gray-400 text-sm">All meals logged for today.</p>
        )}
      </div>
    </main>
  );
}
